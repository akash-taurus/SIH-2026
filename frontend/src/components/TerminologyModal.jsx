import React, { useState, useEffect } from 'react';
import { speakDisasterAudio, stopDisasterAudio } from '../utils/speechUtils';

// Multilingual Terminology Dictionary across all 5 regional languages
const TERMINOLOGY_DT = {
  en: {
    modal_title: "Disaster Terminology & Science Guide",
    subtitle: "Simple citizen-friendly explanations of geotechnical risk metrics and satellite telemetry.",
    tabs: [
      { id: 'all', label: 'All Terms' },
      { id: 'physics', label: 'Slope Physics & FS' },
      { id: 'radar', label: 'Satellites & InSAR' },
      { id: 'rainfall', label: 'Rainfall Triggers' },
      { id: 'risk', label: 'Risk Colors & Evacuation' }
    ],
    items: [
      {
        category: 'physics',
        term: "Factor of Safety (FS)",
        badge: "Core Physics Metric",
        simple_explanation: "The ratio between the mountain slope's holding strength (friction and soil cohesion) versus the gravity force pulling it down.",
        what_it_means: [
          "FS > 1.3: Safe & Stable. The slope can easily resist current rainfall.",
          "FS = 1.0 to 1.2: High Risk / Pre-Failure. The mountain has lost almost all safety margin. Even a moderate shower can trigger a collapse.",
          "FS < 1.0: Active Failure. Sliding forces exceed holding strength. Immediate debris slide is occurring."
        ],
        analogy: "Think of an overloaded elevator cable. If FS drops to 1.0, the cable is at breaking point."
      },
      {
        category: 'radar',
        term: "Sentinel-1 InSAR & Ground Creep",
        badge: "Space Radar Telemetry",
        simple_explanation: "Interferometric Synthetic Aperture Radar (InSAR) uses European Space Agency satellites to measure microscopic millimeter ground movements from orbit.",
        what_it_means: [
          "LOS Velocity (mm/yr): Line-of-Sight speed at which the mountain ridge is moving toward or away from the satellite.",
          "-12.4 mm/yr: Means the ground is steadily sinking and sliding down each year.",
          "Early Warning Value: InSAR catches invisible ground creep weeks before cracks appear on the road or houses."
        ],
        analogy: "Like an ultrasound scan for the mountain that detects hidden stress before a bone breaks."
      },
      {
        category: 'rainfall',
        term: "Caine (1980) Critical Rainfall Threshold",
        badge: "Precipitation Limit",
        simple_explanation: "The mathematical threshold curve (Intensity vs Duration) showing how much rainfall a slope can absorb before water pressure causes it to collapse.",
        what_it_means: [
          "Continuous Rain: 72 hours of steady drizzle can be more dangerous than 1 hour of brief rain because water completely saturates deep rock layers.",
          "Threshold Breach: When the live rain chart line crosses above the red threshold line, immediate mudslides are expected."
        ],
        analogy: "Like a sponge that is completely full of water — any extra drop makes it leak and crumble."
      },
      {
        category: 'physics',
        term: "Pore Water Pressure (u) & Saturation",
        badge: "Soil Mechanics",
        simple_explanation: "The pressure of rainwater trapped inside tiny microscopic pores between soil grains inside the hill.",
        what_it_means: [
          "High Saturation (> 90%): Water pushes soil particles apart, eliminating the natural friction that keeps the hill upright.",
          "Lubrication Effect: The wet soil layer turns into slippery mud, sliding effortlessly down bedrock."
        ],
        analogy: "Like water trapped under a car tire causing hydroplaning on a wet road."
      },
      {
        category: 'risk',
        term: "Risk Severity Tiers & Color Codes",
        badge: "Civil Defense Alerts",
        simple_explanation: "Standardized 4-tier emergency warning levels used by disaster managers and district authorities.",
        what_it_means: [
          "🟢 Low (Green): Normal conditions (FS > 1.3). No evacuation needed.",
          "🟡 Moderate (Yellow): Alert (FS 1.2 - 1.3). Ground movement detected, monitor local weather.",
          "🟠 High (Orange): Warning (FS 1.0 - 1.2). Stage 2 standby evacuation notice. Halt heavy trucks.",
          "🔴 Severe (Red): Red Alert (FS < 1.0). Landslide imminent or occurring. Immediate mandatory evacuation to community shelters."
        ],
        analogy: "Traffic lights for community safety: Green = Safe, Orange = Prepare, Red = Move immediately."
      },
      {
        category: 'risk',
        term: "Evacuation Priority Index",
        badge: "Rescue Decision Formula",
        simple_explanation: "A mathematical score (W_risk × log10(P) × D) that calculates which villages need rescue teams and relief buses first.",
        what_it_means: [
          "Population Density (P): Villages with thousands of children and elders get higher priority.",
          "Road Distance & Passability (D): Remote settlements with blocked escape routes are rescued first before roads are cut off."
        ],
        analogy: "Triage at a hospital: treating the most critical, isolated patients first."
      }
    ]
  },

  kha: {
    modal_title: "কা জিংবাতাই শাফাং কি ক্তিয়েন জিংমা (পাহাৰীয়া বিজ্ঞান)",
    subtitle: "কা জিংবাতাই বা শাই শাফাং কি হিসাব-কিতাব, চেটেলাইট টেলিমেট্ৰি বাদ কা জিংiada.",
    tabs: [
      { id: 'all', label: 'বাৰোহ কি ক্তিয়েন' },
      { id: 'physics', label: 'কা খিন্দেউ & FS' },
      { id: 'radar', label: 'চেটেলাইট InSAR' },
      { id: 'rainfall', label: 'উ স্লাপ' },
      { id: 'risk', label: 'কি ৰং জিংমা & ৰিলিফ' }
    ],
    items: [
      {
        category: 'physics',
        term: "Factor of Safety (FS - সুৰক্ষা গুণক)",
        badge: "হিসাব জিংiada",
        simple_explanation: "কা হিসাব বা পিনী কাতনো কা বোৰ কা খিন্দেউ কা দন বান খং য়া কা জিংত্বা না কা বোৰ টান কা পৃথিৱী (gravity).",
        what_it_means: [
          "FS > ১.৩: Shngain (সুৰক্ষিত)। উ লুম উ লাহ বান য়ালেহ য়া উ স্লাপ।",
          "FS = ১.০ না ১.২: Jingma ba Khraw (বিপদজনক)। কা জিংiada কা লা সাহ তাং খিন্দিয়াত। উ স্লাপ উ লাহ বান পিনত্বা য়া উ লুম।",
          "FS < ১.০: Twamardar (ভূমিস্খলন)। উ লুম উ লা স্দাং ত্বা। পিনকিনৰিয়াহ মাৰদৰ য়া কি লংয়িং।"
        ],
        analogy: "কুম কা জিংকিয়েং বা লাহ বান বহ ১০ টন। লদা দন ৯.৮ টন, কা লা দন হা কা জিংমা বা খ্ৰাৱ।"
      },
      {
        category: 'radar',
        term: "Sentinel-1 InSAR চেটেলাইট",
        badge: "চেটেলাইট ৰাডাৰ",
        simple_explanation: "কা চেটেলাইট ৰাডাৰ না সুয়েন বা জুহ য়া কা জিংখিহ কা খিন্দেউ হা কি মিমি (millimeter).",
        what_it_means: [
          "-১২.৪ মিমি/স্নেম: কা খিন্দেউ কা সিন্তুইদ আৰো ঙাম shapoh মানিয়েহ স্নেম।",
          "মহম লিপা: চেটেলাইট উ য়োহ বান পিনী য়া কা জিংখিহ শ্বা বান পেইত কি স্লাপ হা সুৰক নে য়ীং।"
        ],
        analogy: "কুম কা এক্স-ৰে (X-ray) বা পিনী য়া কা শিয়িং বা লা স্দাং পেইত শ্বা বান খ্দাপ।"
      },
      {
        category: 'rainfall',
        term: "উ স্লাপ বা পিন-ত্বা য়া উ লুম (Rainfall Threshold)",
        badge: "বোৰ উ স্লাপ",
        simple_explanation: "কা হিসাব বা পিনী কাতনো উ স্লাপ উবা ঙাম shapoh খিন্দেউ শ্বা উ লুম উন ত্বা.",
        what_it_means: [
          "স্লাপ জুৰ ৩ sngi: উ স্লাপ বা জপ ৩ sngi উ খাম জিংমা বান য়া উ স্লাপ বা ৱান তাং শি কিন্তা.",
          "পিন্দাপ উম: লদা কা উম কা লা দাপ লুত shapoh খিন্দেউ, কা খিন্দেউ কান ত্বা ৱুত-ৱুত."
        ],
        analogy: "কুম কা স্পঞ্জ বা লা দাপ লুত দা কা উম — তাং শি থোঁক কা উম কা পিন-ঙাম লুত."
      },
      {
        category: 'risk',
        term: "কি ৰং জিংমা (Risk Color Codes)",
        badge: "মহম SDM",
        simple_explanation: "কি ৪ টা কি ৰং বা পিনী য়া কা জিংমা না কা জিংiada.",
        what_it_means: [
          "🟢 জিলিয়েং (Green): Shngain (FS > ১.৩)। য়েম দন জিংমা.",
          "🟡 Stem (Yellow): Peitngor (FS ১.২ - ১.৩)। স্দাং দন জিংখিহ.",
          "🟠 Saw-Stem (Orange): Maham (FS ১.০ - ১.২)। খ্ৰেহ বান লেইত শা কমিউনিটি হল.",
          " Saw (Red): Red AAlert (FS < ১.০)। ত্বা মাৰদৰ! লেইত মাৰদৰ শা কি আশ্ৰয় শিবিৰ."
        ],
        analogy: "কুম কি বাতি ট্ৰেফিক: জিলিয়েং = য়াইদ, সো-স্তেম = খ্ৰেহ, সো = সঙেপ মাৰদৰ."
      }
    ]
  },

  as: {
    modal_title: "ভূমিস্খলন আৰু ভূ-পদাৰ্থ বিজ্ঞানৰ পৰিভাষা সহায়িকা",
    subtitle: "সাধাৰণ নাগৰিক আৰু উদ্ধাৰকাৰী দলৰ বাবে বৈজ্ঞানিক তথ্যৰ সহজ ব্যাখ্যা।",
    tabs: [
      { id: 'all', label: 'সকলো পৰিভাষা' },
      { id: 'physics', label: 'মাটিৰ বিজ্ঞান & FS' },
      { id: 'radar', label: 'উপগ্ৰহ InSAR' },
      { id: 'rainfall', label: 'বৰষুণৰ সীমা' },
      { id: 'risk', label: 'সতৰ্কবাণীৰ ৰং' }
    ],
    items: [
      {
        category: 'physics',
        term: "সুৰক্ষা গুণক (Factor of Safety - FS)",
        badge: "ভৌতিক বিজ্ঞানৰ মানদণ্ড",
        simple_explanation: "পাহাৰে মাটি খহি নপৰাকৈ ধৰি ৰখা শক্তি আৰু মাধ্যাকৰ্ষণ বলে তললৈ টনা শক্তিৰ অনুপাত।",
        what_it_means: [
          "FS > ১.৩: সুৰক্ষিত। পাহাৰৰ মাটি সম্পূৰ্ণ সুস্থিৰ।",
          "FS = ১.০ ৰ পৰা ১.২: উচ্চ আশংকা। পাহাৰৰ সুৰক্ষা ব্যৱধান প্ৰায় শেষ হৈছে। মধ্যমীয়া বৰষুণতো স্খলন হ'ব পাৰে।",
          "FS < ১.০: চৰম সংকট। মাটি খহা আৰম্ভ হৈছে। তাৎক্ষণিকভাবে স্থান ত্যাগ কৰক।"
        ],
        analogy: "এখন দলঙে সৰ্বোচ্চ ১০ টন ওজন ল'ব পাৰে, তাত এতিয়া ৯.৮ টন ভৰ আছে — যিকোনো মুহূৰ্তত বিপদ হ'ব পাৰে।"
      },
      {
        category: 'radar',
        term: "চেন্টিনেল-১ ইনচাৰ (InSAR) উপগ্ৰহ ৰাডাৰ",
        badge: "মহাকাশ ৰাডাৰ তথ্য",
        simple_explanation: "ইউৰোপীয়ান স্পেচ এজেন্সীৰ উপগ্ৰহই মহাকাশৰ পৰা পাহাৰৰ মিলিমিটাৰ স্তৰৰ অতি সূক্ষ্ম গতি নিৰীক্ষণ কৰে।",
        what_it_means: [
          "-১২.৪ মিমি/বছৰ: প্ৰতি বছৰে পাহাৰৰ মাটি তললৈ বহি গৈছে।",
          "আগতীয়া সংকেত: চকুত ফাট মেলা দেখা পোৱাৰ বহু সপ্তাহ আগতেই ইনচাৰে বিপদ ধৰা পেলায়।"
        ],
        analogy: "চিকিৎসকৰ এক্স-ৰে বা আলট্ৰাছাউণ্ডৰ দৰে, যিয়ে হাড় ভঙাৰ আগতেই ভিতৰৰ ফাট ধৰা পেলায়।"
      },
      {
        category: 'rainfall',
        term: "কেইন (Caine 1980) বৰষুণৰ সীমা",
        badge: "বৰষুণৰ বিপদ্বীমা",
        simple_explanation: "পাহাৰে কিমান পৰিমাণৰ বৰষুণ সহ্য কৰিব পাৰে তাৰ গাণিতিক সীমা।",
        what_it_means: [
          "ধাৰাবাহিক বৰষুণ: একেৰাহে ৩ দিন হৈ থকা বৰষুণ ১ ঘণ্টাৰ ধাৰাসাৰ বৰষুণতকৈ বেছি বিপদজনক কাৰণ মাটিৰ গভীৰলৈ পানী সোমাই পৰে।",
          "সীমা অতিক্ৰম: যেতিয়া বৰষুণ ৰঙা সীমা অতিক্ৰম কৰে, লগে লগে ভূমিস্খলন সংঘটিত হয়।"
        ],
        analogy: "পানীত তিতি থকা স্পঞ্জৰ দৰে — বেছি পানী সোমালে ই ফাটি পৰে।"
      },
      {
        category: 'risk',
        term: "সতৰ্কতাৰ ৰং আৰু কাৰ্যপদ্ধতি (Color Codes)",
        badge: "প্ৰশাসনীয় সংকেত",
        simple_explanation: "বিপৰ্যয় ব্যৱস্থাপনা বিভাগৰ দ্বাৰা নিৰ্ধাৰিত ৪ টা ৰঙৰ সংকেত।",
        what_it_means: [
          "🟢 সেউজীয়া (Green): সুৰক্ষিত অৱস্থা (FS > ১.৩)।",
          "🟡 হালধীয়া (Yellow): সতৰ্কতা (FS ১.২ - ১.৩)। বতৰৰ ওপৰত নজৰ ৰাখক।",
          "🟠 কমলা (Orange): উচ্চ সতৰ্কবাণী (FS ১.০ - ১.২)। স্থানান্তৰৰ বাবে সাজু হওক।",
          " ৰঙা (Red): চৰম সতৰ্কবাণী (FS < ১.০)। তাৎক্ষণিকভাৱে আশ্ৰয় শিবিৰলৈ যাওক।"
        ],
        analogy: "ট্ৰেফিক লাইটৰ দৰে: সেউজীয়া = যাওক, কমলা = সাজু হওক, ৰঙা = তৎক্ষণাৎ ৰওক বা সুৰক্ষিত ঠাইলৈ যাওক।"
      }
    ]
  },

  hi: {
    modal_title: "आपदा शब्दावली एवं विज्ञान मार्गदर्शिका",
    subtitle: "भू-तकनीकी जोखिम और उपग्रह डेटा का नागरिकों के लिए सरल एवं स्पष्ट विवरण।",
    tabs: [
      { id: 'all', label: 'सभी शब्द' },
      { id: 'physics', label: 'सुरक्षा कारक (FS)' },
      { id: 'radar', label: 'इनसार उपग्रह' },
      { id: 'rainfall', label: 'वर्षा सीमा' },
      { id: 'risk', label: 'कलर कोड व निकासी' }
    ],
    items: [
      {
        category: 'physics',
        term: "सुरक्षा कारक (Factor of Safety - FS)",
        badge: "मूल भौतिकी पैमाना",
        simple_explanation: "पहाड़ की मिट्टी की पकड़ने की शक्ति और नीचे खींचने वाले गुरुत्वाकर्षण बल का अनुपात।",
        what_it_means: [
          "FS > 1.3: सुरक्षित एवं स्थिर। ढलान पूरी तरह मजबूत है।",
          "FS = 1.0 से 1.2: उच्च जोखिम (पूर्व-विफलता)। सुरक्षा मार्जिन खत्म हो चुका है। थोड़ी सी भी बारिश से भूस्खलन हो सकता है।",
          "FS < 1.0: सक्रिय भूस्खलन। मलबा गिरना शुरू हो चुका है, तुरंत सुरक्षित स्थान पर जाएं।"
        ],
        analogy: "एक लिफ्ट की अधिकतम क्षमता 10 लोगों की है और उसमें 9.8 लोग खड़े हैं — यानी वह कभी भी गिर सकती है।"
      },
      {
        category: 'radar',
        term: "सेंटिनल-1 इनसार (InSAR) उपग्रह",
        badge: "अंतरिक्ष रडार निगरानी",
        simple_explanation: "यूरोपीय अंतरिक्ष एजेंसी के उपग्रह जो अंतरिक्ष से जमीन के मिलीमीटर स्तर के धंसाव को मापते हैं।",
        what_it_means: [
          "-12.4 मिमी/वर्ष: पहाड़ की ढलान हर साल नीचे की ओर खिसक रही है।",
          "पूर्व चेतावनी: सड़कों पर दरारें दिखने से कई हफ्ते पहले ही उपग्रह हलचल पकड़ लेता है।"
        ],
        analogy: "पहाड़ का एक्स-रे / सीटी स्कैन, जो दरार बाहर आने से पहले अंदरूनी कमजोरी बता देता है।"
      },
      {
        category: 'rainfall',
        term: "केन (Caine 1980) वर्षा सीमा",
        badge: "वर्षा की अंतिम सीमा",
        simple_explanation: "वह अधिकतम बारिश जिसे पहाड़ सहन कर सकता है, उसके बाद मिट्टी का दबाव ढलान को ढहा देता है।",
        what_it_means: [
          "लगातार बारिश: 3 दिनों की रिमझिम बारिश 1 घंटे की तेज बारिश से ज्यादा घातक होती है क्योंकि पानी गहराई तक बैठ जाता है।",
          "सीमा पार: जब बारिश लाल रेखा से ऊपर जाती है, तो भूस्खलन तुरंत शुरू होता है।"
        ],
        analogy: "पूरी तरह पानी से भीगे स्पंज की तरह — और पानी डालने पर वह टूटकर बिखर जाता है।"
      },
      {
        category: 'risk',
        term: "कलर कोड एवं आपदा स्तर (AAlert Tiers)",
        badge: "आपदा प्रबंधन अलर्ट",
        simple_explanation: "प्रशासन द्वारा घोषित 4 स्तरों के आपातकालीन चेतावनी रंग।",
        what_it_means: [
          "🟢 हरा (Green): सुरक्षित स्थिति (FS > 1.3)।",
          "🟡 पीला (Yellow): सतर्क रहें (FS 1.2 - 1.3)। मौसम पर नजर रखें।",
          "🟠 नारंगी (Orange): चेतावनी (FS 1.0 - 1.2)। राहत शिविर में जाने की तैयारी करें।",
          " लाल (Red): रेड अलर्ट (FS < 1.0)। तुरंत अपना घर छोड़कर राहत केंद्र जाएं।"
        ],
        analogy: "ट्रैफिक सिग्नल की तरह: हरा = सुरक्षित, नारंगी = तैयार रहें, लाल = तुरंत सुरक्षित जगह पहुंचें।"
      }
    ]
  },

  grt: {
    modal_title: "Kenani aro ·a Beani Kobor Skiani (Terminology Guide)",
    subtitle: "·a be·ani aro satellite telemetry-ko rongtalgipa dake skiani.",
    tabs: [
      { id: 'all', label: 'Gimik Kattarang' },
      { id: 'physics', label: '·ani Bil & FS' },
      { id: 'radar', label: 'Satellite InSAR' },
      { id: 'rainfall', label: 'Mikka' },
      { id: 'risk', label: 'Kenani Rongrang' }
    ],
    items: [
      {
        category: 'physics',
        term: "Factor of Safety (FS - Rak·ani Hisab)",
        badge: "Geotechnical Hisab",
        simple_explanation: "·bri a·a rim·chakkapani bil aro a·a ka·maona sol·solani bilni hisab.",
        what_it_means: [
          "FS > ১.৩: Naljoka (সুৰক্ষিত)। ·bri an·seng donga.",
          "FS = ১.০ na ১.২: Bilonggipa Kenani (বিপদজনক)। ·ani rak·ani tang khindiyat donga. Mikka bilongahaode be·gen.",
          "FS < ১.০: Be·enga (ভূমিস্খলন)। ·a be·baenga. Manderang mardor katbo."
        ],
        analogy: "Jol·jol 10 ton gariko sale 9.8 ton bolrang dongani gita — kenani donga."
      },
      {
        category: 'radar',
        term: "Sentinel-1 InSAR Satellite",
        badge: "Space Radar",
        simple_explanation: "Salgi gita satellite radar a·a tang·engako millimeter gita niani.",
        what_it_means: [
          "-১২.৪ মিমি/বিলসি: ·a bilsiantio ka·maona tang·enga.",
          "Skang Niani: Ramao a·pala a·rikkanggipa a·selko satellite skang niksoaha."
        ],
        analogy: "Doctorni X-ray niani gita — a·a bobilangako skang niksona man·a."
      },
      {
        category: 'risk',
        term: "Kenani Rongrang (Color Codes)",
        badge: "SDM AAlert",
        simple_explanation: "Kenani obostako u·iatna rong 4 donga.",
        what_it_means: [
          "🟢 Tangsek (Green): Naljoka (FS > ১.৩)।",
          "🟡 Rimit (Yellow): Ni·rokbo (FS ১.২ - ১.৩)।",
          "🟠 Bokdel (Orange): Tarisobo (FS ১.০ - ১.২)। Community Hall-ona re·angna taribo.",
          " Gitchak (Red): Red AAlert (FS < ১.০)। Mardor relief shelter-ona katbo!"
        ],
        analogy: "Traffic light gita: Tangsek = Re·angbo, Bokdel = Tarisobo, Gitchak = Katbo."
      }
    ]
  }
};

/**
 * TerminologyModal: Interactive High-Density Scientific Help & Glossary Section
 * Features category filtering, plain-language analogies, and localized Text-To-Speech voice readouts.
 */
export default function TerminologyModal({
  isOpen = false,
  onClose = () => {},
  language = 'en'
}) {
  const [activeTab, setActiveTab] = useState('all');
  const [playingTermIdx, setPlayingTermIdx] = useState(null);

  const langKey = ['en', 'kha', 'grt', 'hi', 'as'].includes(language) ? language : 'en';
  const content = TERMINOLOGY_DT[langKey] || TERMINOLOGY_DT.en;

  // Stop audio on modal close or unmount
  useEffect(() => {
    if (!isOpen) {
      stopDisasterAudio();
      setPlayingTermIdx(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredItems =
    activeTab === 'all'
      ? content.items
      : content.items.filter((item) => item.category === activeTab);

  const handleSpeakTerm = (item, idx) => {
    if (playingTermIdx === idx) {
      stopDisasterAudio();
      setPlayingTermIdx(null);
      return;
    }

    const detailsLabel = langKey === 'hi' ? 'मुख्य विवरण:' : langKey === 'as' ? 'মুখ্য বিৱৰণ:' : 'Details:';
    const analogyLabel = langKey === 'hi' ? 'दैनिक जीवन से उदाहरण:' : langKey === 'as' ? 'দৈনন্দিন জীৱনৰ উদাহৰণ:' : 'Everyday analogy:';
    const spokenText = `${item.term}. ${item.simple_explanation}. ${detailsLabel} ${item.what_it_means.join('. ')}. ${analogyLabel} ${item.analogy}`;

    speakDisasterAudio({
      text: spokenText,
      language: langKey,
      onStart: () => setPlayingTermIdx(idx),
      onEnd: () => setPlayingTermIdx(null),
      onError: () => setPlayingTermIdx(null)
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/75 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white border-2 border-black shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col font-sans">
        {/* Header */}
        <div className="bg-black text-white p-4 flex items-center justify-between border-b-2 border-black shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="w-7 h-7 bg-white text-black font-black flex items-center justify-center text-sm">
              
            </span>
            <div>
              <h2 className="text-sm sm:text-base font-black uppercase tracking-tight">
                {content.modal_title}
              </h2>
              <p className="text-[11px] text-gray-300 font-mono">
                {content.subtitle}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              stopDisasterAudio();
              setPlayingTermIdx(null);
              onClose();
            }}
            className="hover:bg-gray-800 text-white font-bold px-3 py-1 text-sm border border-white cursor-pointer transition-colors"
          >
            ✕ Close
          </button>
        </div>

        {/* Category Tabs */}
        <div className="bg-gray-100 p-2 border-b border-black flex flex-wrap items-center gap-1.5 shrink-0">
          {content.tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1 text-xs font-mono font-bold border transition-colors cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-black text-white border-black'
                  : 'bg-white text-black border-gray-300 hover:border-black'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Terminology Cards List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/60">
          {filteredItems.map((item, idx) => (
            <div
              key={`term-${idx}`}
              className="bg-white border-2 border-black p-4 space-y-2.5 shadow-xs"
            >
              {/* Card Header */}
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 pb-2">
                <div className="flex items-center gap-2">
                  <span className="text-base"></span>
                  <h3 className="font-black text-black text-sm sm:text-base tracking-tight">
                    {item.term}
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className="bg-gray-100 text-black border border-black px-2 py-0.5 text-[10px] font-mono font-bold uppercase">
                    {item.badge}
                  </span>
                  {/* Voice Readout Button */}
                  <button
                    type="button"
                    onClick={() => handleSpeakTerm(item, idx)}
                    className={`px-2.5 py-0.5 text-[10px] font-mono font-bold border border-black cursor-pointer transition-colors flex items-center gap-1 ${
                      playingTermIdx === idx
                        ? 'bg-red-600 text-white animate-pulse'
                        : 'bg-white hover:bg-black hover:text-white text-black'
                    }`}
                  >
                    <span>{playingTermIdx === idx ? ' Stop Voice' : ' Listen Audio'}</span>
                  </button>
                </div>
              </div>

              {/* Simple Definition */}
              <p className="text-xs sm:text-sm text-gray-900 leading-relaxed font-medium">
                {item.simple_explanation}
              </p>

              {/* Breakdown Points */}
              <div className="bg-gray-50 border-l-4 border-black p-2.5 space-y-1 text-xs text-gray-800 font-sans">
                {item.what_it_means.map((pt, pIdx) => (
                  <div key={`pt-${pIdx}`} className="flex items-start gap-1.5">
                    <span className="text-black font-bold">•</span>
                    <span>{pt}</span>
                  </div>
                ))}
              </div>

              {/* Everyday Analogy */}
              {item.analogy && (
                <div className="text-[11px] font-mono text-gray-700 bg-yellow-50/70 border border-yellow-300 p-2 flex items-center gap-1.5">
                  <span className="text-sm"></span>
                  <span><b>Simple Analogy:</b> {item.analogy}</span>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="bg-white p-3 border-t-2 border-black flex flex-wrap items-center justify-between gap-2 shrink-0 text-xs font-mono">
          <span className="text-gray-600">
            Source: GSI • ISRO Disaster Management SuApport • USGS Geotechnical Guidelines
          </span>
          <button
            type="button"
            onClick={() => {
              stopDisasterAudio();
              setPlayingTermIdx(null);
              onClose();
            }}
            className="bg-black hover:bg-gray-800 text-white font-bold px-4 py-1.5 border border-black uppercase cursor-pointer"
          >
            Got It
          </button>
        </div>
      </div>
    </div>
  );
}
