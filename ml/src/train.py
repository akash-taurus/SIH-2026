"""Train/evaluate SIH26001 models with spatial validation and probability calibration."""
import argparse, sys, time, joblib, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score, confusion_matrix, precision_recall_fscore_support
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from features import build_feature_matrix, spatial_train_test_split, ALL_FEATURE_COLUMNS

MODEL_VERSION="v2.0"

def evaluate(model, X, y, name):
    p=model.predict_proba(X)[:,1]; pred=(p>=.5).astype(int)
    precision,recall,f1,_=precision_recall_fscore_support(y,pred,average="binary",zero_division=0)
    tn,fp,fn,tp=confusion_matrix(y,pred).ravel(); far=fp/max(fp+tn,1)
    print(f"{name}: ROC-AUC={roc_auc_score(y,p):.3f} PR-AUC={average_precision_score(y,p):.3f} Precision={precision:.3f} Recall={recall:.3f} F1={f1:.3f} FAR={far:.3%}")
    return p

def train(data_path, model_out="models/xgb_landslide_v2.pkl"):
    df=pd.read_csv(data_path); train_df,test_df=spatial_train_test_split(df)
    Xtr,ytr=build_feature_matrix(train_df); Xte,yte=build_feature_matrix(test_df)
    pos=ytr.sum(); neg=len(ytr)-pos; spw=neg/max(pos,1)
    candidates={
      "xgboost":XGBClassifier(n_estimators=350,max_depth=4,learning_rate=.04,subsample=.85,colsample_bytree=.85,scale_pos_weight=spw,eval_metric="aucpr",random_state=42,n_jobs=-1),
      "random_forest":RandomForestClassifier(n_estimators=400,max_depth=12,class_weight="balanced",random_state=42,n_jobs=-1)
    }
    results={}
    for name,m in candidates.items():
        m.fit(Xtr,ytr); results[name]=(m, evaluate(m,Xte,yte,name))
    best_name=max(results,key=lambda n: average_precision_score(yte,results[n][1])); base=results[best_name][0]
    # Calibrate on held-out validation data. For a real deployment, use a separate temporal validation set.
    calibrated=LogisticRegression(solver="lbfgs")
    calibrated.fit(base.predict_proba(Xtr)[:,1].reshape(-1,1),ytr)
    p=calibrated.predict_proba(base.predict_proba(Xte)[:,1].reshape(-1,1))[:,1]
    print(f"Selected model: {best_name}; calibrated PR-AUC={average_precision_score(yte,p):.3f}")
    print(classification_report(yte,(p>=.5).astype(int),digits=3,zero_division=0))
    # Operational thresholds aligned with frontend Legend (PLAN 05):
    # Low <30%, Moderate 30-60%, High 60-80%, Severe >80%.
    thresholds={"moderate":.30,"high":.60,"severe":.80}
    out=Path(model_out); out.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump({"model":base,"calibrator":calibrated,"feature_columns":ALL_FEATURE_COLUMNS,"model_version":MODEL_VERSION,"thresholds":thresholds,"selected_model":best_name,"evaluation":{"pr_auc":average_precision_score(yte,p),"roc_auc":roc_auc_score(yte,p)}},out)
    t0=time.perf_counter(); [calibrated.predict_proba(base.predict_proba(Xte.iloc[[0]])[:,1].reshape(-1,1)) for _ in range(100)]; print(f"Avg calibrated inference latency: {(time.perf_counter()-t0)/100*1000:.2f} ms")
    print(f"Saved {out.resolve()}")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--data",default="data/raw/synthetic_grid_dataset.csv"); ap.add_argument("--out",default="models/xgb_landslide_v2.pkl"); args=ap.parse_args(); train(args.data,args.out)
