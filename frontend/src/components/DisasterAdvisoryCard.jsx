import React, { useState, useEffect } from 'react';
import { speakDisasterAudio, stopDisasterAudio } from '../utils/speechUtils';

// Native Multilingual Disaster dvisories Dictionary in Bengali-ssamese, Devanagari & Latin Scripts
const ADVISORY_DT = {
  'Z-SHL-01': {
    en: {
      location: "Shillong East Ridge & UApper Shillong (1,496m MSL)",
      tier: "SEVERE RISK (Red Alert / Immediate action)",
      badgeColor: "bg-red-600 text-white",
      summary: "The ridge is in an active critical state with Factor of Safety FS = 0.88. Heavy cloudburst precipitation has saturated the weathered quartz-schist layer (98% saturation), with pore pressure u exceeding critical shear strength. Satellite InSAR indicates -14.2 mm/yr subsidence.",
      trigger: "ny additional rainfall exceeding 15 mm/h will cause rapid debris avalanches down towards the Shillong bypass corridor.",
      actions: [
        "Mandatory immediate evacuation of vulnerable families living below the ridge crown.",
        "Total roadblock and police barricading of the uApper Shillong bypass.",
        "NDRF search & rescue squads pre-deployed at Happy Valley command base."
      ]
    },
    kha: {
      location: "লুম শিল্লং & আপাৰ শিল্লং (১,৪৯৬ মি)",
      tier: "জিংমা বা খ্ৰাৱ এহ (Red Alert / পিনকিনৰিয়াহ মাৰদৰ)",
      badgeColor: "bg-red-600 text-white",
      summary: "উ লুম শিল্লং উ দন মিন্তা হা কা জিংমা বা খ্ৰাৱ এহ (Factor of Safety FS = ০.৮৮)। উ স্লাপ উবা জুৰ উ লা পিনঙাম লুত য়া কা উম শাপোহ খিন্দেউ (৯৮% চেচুৰেশ্বন), বাদ কা খিন্দেউ কা লা স্দাং সিন্তুইদ হা মাদান (-১৪.২ মিমি/স্নেম)।",
      trigger: "লদা উ স্লাপ উ নাং জুৰ পালাত য়া কা ১৫ মিমি/কিন্তা, কা খিন্দেউ কান ত্বা ৱুত-ৱুত শা সুৰক বাহ শিল্লং বাইপাছ।",
      actions: [
        "পিনকিনৰিয়াহ মাৰদৰ য়া বাৰোহ কি লংয়িং কিবা সাহ হাৰুম উ লুম শা কি জাকা ৰিয়েহ বা শ্ঙায়িন।",
        "খাং ক্পুত য়া কা সুৰক বাহ আপাৰ শিল্লং বাইপাছ না কা ব্যান্তা কি কালী বাৰোহ।",
        "কি কিনহুন NDRF কি দেই বান দন লিপা হা হেপ্পী ভেলী বান য়াৰাপ মাৰদৰ।"
      ]
    },
    grt: {
      location: "শিল্লং আ·ব্ৰি & আপাৰ শিল্লং (১,৪৯৬ মি)",
      tier: "বাতেবাতে বিলংগিপা কেনানি (Red AAlert / কাতনা কাম কা·আনি)",
      badgeColor: "bg-red-600 text-white",
      summary: "শিল্লং আ·ব্ৰি দা·অ বাতেবাতে বিলংগিপা কেনানি অবস্থাত দংআ (Factor of Safety FS = ০.৮৮)। মিক্কা দাল·এ গা·আকে আ·আ চিমিক গিমিক স্ৰাপমানাহা (৯৮% চেচুৰেশ্বন), আৰো InSAR চেটেলাইট -১৪.২ মিমি/বিলসি আ·আ ৰু·এঙাকো নিসাহা।",
      trigger: "মিক্কা ১৫ মিমি/কিন্তা গিতা দাল·দাপাহাওদে, আ·আ বে·এ শিল্লং বাইপাছ ৰামাত চামপেংআতগেন।",
      actions: [
        "আ·ব্ৰি কা·মাও দংগিপা মান্দেৰাংকো মাৰদৰ গিপিন বিয়াপঅনা কাতাতবো।",
        "আপাৰ শিল্লং বাইপাছ ৰামাকো গাৰীৰাংনা চিপতকবো।",
        "NDRF দলৰাং হেপ্পী ভেলীত তাৰিয়ানিকো তাৰিস-চিংবো।"
      ]
    },
    hi: {
      location: "शिलांग ईस्ट रिज एवं अपर शिलांग (1,496 मी एमएसएल)",
      tier: "अत्यधिक गंभीर जोखिम (रेड अलर्ट / तत्काल निकासी)",
      badgeColor: "bg-red-600 text-white",
      summary: "पहाड़ी ढलान वर्तमान में ढहने की कगार पर है (सुरक्षा कारक FS = 0.88)। मूसलाधार बारिश से मिट्टी 98% संतृप्त हो चुकी है और उपग्रह इनसार ने -14.2 मिमी/वर्ष की गति से धंसाव दर्ज किया है।",
      trigger: "यदि अगले कुछ घंटों में 15 मिमी/घंटा से अधिक वर्षा होती है, तो मलबा तेजी से शिलांग बाईपास पर गिर जाएगा।",
      actions: [
        "कगार के नीचे रहने वाले सभी परिवारों को तुरंत सुरक्षित राहत शिविरों में भेजें।",
        "अपर शिलांग बाईपास को सभी प्रकार के वाहनों के लिए तुरंत बंद करें।",
        "एनडीआरएफ टीमों को हैप्पी वैली बेस पर हाई अलर्ट पर तैनात करें।"
      ]
    },
    as: {
      location: "শ্বিলং ইষ্ট ৰিজ আৰু আপাৰ শ্বিলং (১,৪৯৬ মি)",
      tier: "চৰম বিপদৰ সতৰ্কবাণী (ৰঙা সংকেত / তাৎক্ষণিক পদক্ষেপ)",
      badgeColor: "bg-red-600 text-white",
      summary: "পাহাৰৰ ঢাল বৰ্তমান অতিশয় সংকটজনক অৱস্থাত আছে (সুৰক্ষা গুণক FS = 0.88)। প্ৰবল বৰষুণৰ ফলত মাটি ৯৮% জলমগ্ন হৈ পৰিছে আৰু ইনচাৰ উপগ্ৰহই -১৪.২ মিমি/বছৰ নিম্নমুখী গতি ধৰা পেলাইছে।",
      trigger: "১৫ মিমি/ঘণ্টাতকৈ অধিক বৰষুণ হ'লে শ্বিলং বাইপাছলৈ প্ৰবল মাটিৰ স্খলন হ'ব।",
      actions: [
        "পাহাৰৰ তলত বাস কৰা পৰিয়ালসমূহক অনতিপলমে সুৰক্ষিত আশ্ৰয় শিবিৰলৈ স্থানান্তৰ কৰক।",
        "আপাৰ শ্বিলং বাইপাছ পথত সকলো যান-বাহন চলাচল বন্ধ কৰক।",
        "হেপ্পী ভেলী শিবিৰত NDRF দলক সাজু কৰি ৰাখক।"
      ]
    }
  },

  'SET-LIT-03': {
    en: {
      location: "Laitlyngkot Slope Dwellings (SH-5 Corridor)",
      tier: "HIGH RISK (Orange Alert / Stage 2 Standby)",
      badgeColor: "bg-orange-500 text-white",
      summary: "The slope is currently in a critical pre-failure stage with Factor of Safety FS = 1.14 (resisting safety margin down to 14%). Satellite InSAR confirms active downward tension creep of -12.4 mm/yr along the uApper ridge crown.",
      trigger: " sudden cloudburst exceeding 25 mm/h will cause full pore water pressure saturation, triggering a rapid landslide down onto the SH-5 highway.",
      actions: [
        "Put 1,480 residents on Stage 2 Standby Evacuation notice with community hall shelter preApped.",
        "Halt heavy commercial trucks on SH-5 to prevent vibrational failure.",
        "Stage bulldozers and PWD clearance units at Pynursla (8.5 km away)."
      ]
    },
    kha: {
      location: "লাইতলিংকট পাহাৰীয়া বসতি (সুৰক বাহ SH-5)",
      tier: "জিংমা বা খ্ৰাৱ (Orange AAlert / খ্ৰেহ বান পিনকিনৰিয়াহ)",
      badgeColor: "bg-orange-500 text-white",
      summary: "কা জাকা লাইতলিংকট কা দন মিন্তা হা কা জিংমা কাবা খ্ৰাৱ নামাৰ কা খিন্দেউ কা লা স্দাং সিন্তুইদ হা মাদান (-১২.৪ মিমি/স্নেম) বাদ লা দন কি জিংপায়িত হা খ্লিয়েহ লুম (FS = ১.১৪, কা জিংয়াদা কা সাহ তাং ১৪%)।",
      trigger: "লদা উ স্লাপ উ ৱান জুৰ পালাত য়া কা ২৫ মিমি/কিন্তা, কা উম স্লাপ কান পিন্দাপ য়া কা খিন্দেউ বাদ কা লুম কান ত্বা ৱুত-ৱুত শা কা সুৰক বাহ SH-5।",
      actions: [
        "মাহাম য়া কি ১,৪৮০ ঙুত কি নোংশোংশ্নং বান পিনখ্ৰেহ বান লেইত শা কমিউনিটি হল।",
        "খাং লাদ য়া কি ত্ৰক হেহ বান য়াইদ হা সুৰক বাহ SH-5 খ্নাং বান য়ম পিনখিহ য়া উ লুম।",
        "বুহ লিপা য়া কি JCB বাদ কি কোৰ পিনখুইদ সুৰক হা পাইনুৰ্সলা (৮.৫ কিমি না লাইতলিংকট)।"
      ]
    },
    grt: {
      location: "লাইতলিংকট আ·ব্ৰি আ·কাৱে (SH-5 ৰামা)",
      tier: "বিলংগিপা কেনানি (Orange Alert / কাতনা তাৰিসোআনি)",
      badgeColor: "bg-orange-500 text-white",
      summary: "লাইতলিংকট আ·ব্ৰি আ·কাৱে দা·অ কেনবেগিপা অবস্থাত দংআ (FS = ১.১৪, আ·আনি ৰাক·আনি তাং ১৪% দংআ)। চেটেলাইট আ·আ বিলসিত -১২.৪ মিমি তাং·এঙাকো নিসাহা।",
      trigger: "মিক্কা ২৫ মিমি/কিন্তা গিতা বিলংগাহাওদে, আ·আ বে·এ SH-5 ৰামাকো চামপেংআতগেন।",
      actions: [
        "সাক ১,৪৮০ মান্দেৰাংকো কমিউনিটি হল-অনা গাকাতনা তাৰিসচিংবো।",
        "SH-5 ৰামা গিতা দাল·গিপা গাৰীৰাংকো ৰে·আমিককো চামপেংবো।",
        "পাইনুৰ্সলাত (৮.৫ কিমি চেল·আও) JCB আৰো PWD দলৰাংকো তাৰিসোআতবো।"
      ]
    },
    hi: {
      location: "लैटलिंगकोट ढलान बस्तियां (SH-5 राजमार्ग गलियारा)",
      tier: "उच्च जोखिम (ऑरेंज अलर्ट / स्टेज 2 स्टैंडबाय)",
      badgeColor: "bg-orange-500 text-white",
      summary: "लैटलिंगकोट की ढलान वर्तमान में पूर्व-विफलता की संवेदनशील स्थिति में है (सुरक्षा कारक FS = 1.14, सुरक्षा मार्जिन केवल 14% बचा है)। इनसार उपग्रह ने कगार पर -12.4 मिमी/वर्ष की गति से दरारें और धंसाव दर्ज किया है।",
      trigger: "यदि 25 मिमी/घंटा से अधिक तीव्र बौछार होती है, तो जलभराव के दबाव से ढलान तुरंत SH-5 सड़क पर ढह जाएगी।",
      actions: [
        "1,480 निवासियों को स्टेज 2 स्टैंडबाय पर रखें और सामुदायिक भवन में राहत शिविर तैयार करें।",
        "कंपन से होने वाले भूस्खलन को रोकने के लिए SH-5 पर भारी ट्रकों का प्रवेश रोकें।",
        "पिनुर्सला (8.5 किमी दूर) पर बुलडोजर और मलबे हटाने वाले उपकरण पहले से तैनात करें।"
      ]
    },
    as: {
      location: "লাইতলিংকট পাহাৰীয়া বসতি (SH-5 ঘাইপথ অঞ্চল)",
      tier: "উচ্চ সতৰ্কতা (কমলা সংকেত / দ্বিতীয় পৰ্যায়ৰ সষ্টমতা)",
      badgeColor: "bg-orange-500 text-white",
      summary: "লাইতলিংকট অঞ্চলত পাহাৰীয়া মাটি বৰ্তমান সংকটজনক অৱস্থাত আছে (সুৰক্ষা গুণক FS = 1.14, সুৰক্ষাৰ ব্যৱধান মাত্ৰ ১৪%)। উপগ্ৰহ ইনচাৰে ওপৰৰ পাহাৰত -১২.৪ মিমি/বছৰ গতিত ফাট মেলা প্ৰত্যক্ষ কৰিছে।",
      trigger: "২৫ মিমি/ঘণ্টাতকৈ অধিক প্ৰবল বৰষুণ হ'লে মাটি খহি SH-5 ঘাইপথ সম্পূৰ্ণৰূপে বন্ধ হৈ পৰিব।",
      actions: [
        "১,৪৮০ গৰাকী বাসিন্দাক স্থানান্তৰৰ বাবে সাজু থাকিবলৈ কওক আৰু আশ্ৰয় শিবিৰ মুকলি কৰক।",
        "পাহাৰৰ কম্পন ৰোধ কৰিবলৈ SH-5 পথত গধুৰ ট্ৰাক চলাচল নিষিদ্ধ কৰক।",
        "পাইনোৰ্সলাত (৮.৫ কিমি দূৰত) জৰুৰীভাৱে জেচিবি আৰু পথ চাফা কৰা দল সাজু ৰাখক।"
      ]
    }
  },

  'Z-CHR-02': {
    en: {
      location: "Sohra Plateau & Cherrapunji Escarpment (1,430m MSL)",
      tier: "HIGH RISK (Orange Alert / Active Shear Warning)",
      badgeColor: "bg-orange-500 text-white",
      summary: "The Sohra escarpment face exhibits critical shear stresses (FS = 1.09). Severe monsoon runoff along the limestone gorges has widened toe fractures with Sentinel-1 InSAR detecting -18.6 mm/yr scarp subsidence.",
      trigger: "Intense rainfall exceeding 30 mm/h will cause sudden rockfalls and debris avalanches onto the Shella border route.",
      actions: [
        "Evacuate Cherrapunji Rim families to Sohra Community Health Centre shelters.",
        "Deploy patrol vehicles on SH-5 Sohra-Shella road to monitor boulder falls.",
        "Issue SMS weather warnings to tourism operators and local taxi unions."
      ]
    },
    kha: {
      location: "খ্লিয়েহৰিয়াত & লুম চোহৰা (১,৪৩০ মি)",
      tier: "জিংমা বা খ্ৰাৱ (Orange AAlert / মাহাম না কা মাও-ত্বা)",
      badgeColor: "bg-orange-500 text-white",
      summary: "কা জাকা চোহৰা কা দন হা কা জিংমা কাবা খ্ৰাৱ (FS = ১.০৯) নামাৰ উ স্লাপ উবা জুৰ উ লা পিনপায়িত য়া কি মাওসিয়াং বাদ InSAR চেটেলাইট উ পিনী বা কা খিন্দেউ কা সিন্তুইদ -১৮.৬ মিমি/স্নেম।",
      trigger: "লদা উ স্লাপ উ জুৰ পালাত য়া কা ৩০ মিমি/কিন্তা, কি মাও বাহ কিন ত্বা বাদ ঙাম শা সুৰক শেল্লা।",
      actions: [
        "পিনকিনৰিয়াহ য়া কি লংয়িং না চোহৰা ৰিম শা চোহৰা CHC।",
        "ফাহ য়া কি পুলিত পেত্ৰল বান পেইতনগৰ য়া কা সুৰক চোহৰা-শেল্লা।",
        "ফাহ SMS বান মাহাম য়া কি কালী কামাই বাদ কি নোংলেইত জ্ঙোহকাই।"
      ]
    },
    grt: {
      location: "চোহৰা আ·কাৱে & চেৰাপুঞ্জী (১,৪৩০ মি)",
      tier: "বিলংগিপা কেনানি (Orange Alert / ৰো·অং গা·আকানি)",
      badgeColor: "bg-orange-500 text-white",
      summary: "চোহৰা আ·ব্ৰি দা·অ কেনানি অবস্থাত দংআ (FS = ১.০৯)। মিক্কা দাল·এ আ·আ ৰো·অংৰাং বে·এঙা আৰো চেটেলাইট -১৮.৬ মিমি/বিলসি তাং·এঙাকো নিসাহা।",
      trigger: "মিক্কা ৩০ মিমি/কিন্তা গিতা দাল·আহাওদে, ৰো·অং দাল·গিপাৰাং শেল্লা ৰামাপোনা গা·আকনানগেন।",
      actions: [
        "চোহৰা ৰিমনি মান্দেৰাংকো চোহৰা CHC বিয়াপঅনা কাতাতবো।",
        "চোহৰা-শেল্লা ৰামা গিতা পুলিচ পেত্ৰলৰাংকো নিসানাতায়িবো।",
        "ৰে·ৰবাগিপানা আৰো গাৰী চালগিপানা SMS কবোৰ অন·আতবো।"
      ]
    },
    hi: {
      location: "सोहरा पठार एवं चेरापूंजी कगार (1,430 मी एमएसएल)",
      tier: "उच्च जोखिम (ऑरेंज अलर्ट / भूस्खलन चेतावनी)",
      badgeColor: "bg-orange-500 text-white",
      summary: "सोहरा कगार पर अत्यधिक अपरूपण तनाव बना हुआ है (FS = 1.09)। भारी मानसूनी रिसाव के कारण उपग्रह इनसार ने -18.6 मिमी/वर्ष की गति से विस्थापन दर्ज किया है।",
      trigger: "30 मिमी/घंटा से अधिक वर्षा होने पर चट्टानें और मलबा शेल्ला सीमा मार्ग पर गिर सकते हैं।",
      actions: [
        "सोहरा रिम के परिवारों को सामुदायिक स्वास्थ्य केंद्र के राहत शिविरों में पहुंचाएं।",
        "सोहरा-शेल्ला सड़क पर गश्ती दल तैनात करें।",
        "पर्यटकों और स्थानीय वाहन संघों को आपातकालीन एसएमएस चेतावनी भेजें।"
      ]
    },
    as: {
      location: "চোহৰা মালভূমি আৰু চেৰাপুঞ্জী (১,৪৩০ মি)",
      tier: "উচ্চ সতৰ্কতা (কমলা সংকেত / শিল খহাৰ আশংকা)",
      badgeColor: "bg-orange-500 text-white",
      summary: "চোহৰাৰ খাড়া পাহাৰত ভূমিস্খলনৰ গভীৰ আশংকা আছে (FS = 1.09)। প্ৰবল বৰষুণৰ ফলত ইনচাৰ উপগ্ৰহই -১৮.৬ মিমি/বছৰ গতিত পাহাৰ খহি পৰাৰ তথ্য দিছে।",
      trigger: "৩০ মিমি/ঘণ্টাতকৈ অধিক বৰষুণ হ'লে চেলা সংযোগী পথত প্ৰকাণ্ড শিল খহি পৰিব।",
      actions: [
        "চেৰাপুঞ্জী ৰিমৰ লোকসকলক চোহৰা চিকিৎসালয়ৰ আশ্ৰয় শিবিৰলৈ নিব লাগে।",
        "চোহৰা-চেলা পথত নিৰীক্ষণকাৰী দল মোতায়েন কৰক।",
        "পৰ্যটক আৰু বাহন চালকসকললৈ সতৰ্কতামূলক SMS প্ৰেৰণ কৰক।"
      ]
    }
  }
};

/**
 * DisasterAdvisoryCard: Live Native Language Multi-Modal Early Warning AAdvisory
 * SuApports English, Khasi (কা ক্তিয়েন খাসী), Garo (আ·চিক কু·সিক), Hindi (हिन्दी), ssamese (অসমীয়া).
 * Includes Text-To-Speech audio readout for rural citizens & field responders.
 */
export default function DisasterAdvisoryCard({
  selectedZone = null,
  language = 'en'
}) {
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const activeZoneId = selectedZone?.zone_id || 'Z-SHL-01';
  const activeAdvisory =
    ADVISORY_DT[activeZoneId] ||
    (activeZoneId === 'Z-CHR-02' ? ADVISORY_DT['Z-CHR-02'] : ADVISORY_DT['SET-LIT-03']) ||
    ADVISORY_DT['Z-SHL-01'];

  const langKey = ['en', 'kha', 'grt', 'hi', 'as'].includes(language) ? language : 'en';
  const content = activeAdvisory[langKey] || activeAdvisory.en;

  // Stop audio on unmount or language/zone change
  useEffect(() => {
    return () => {
      stopDisasterAudio();
      setIsPlayingAudio(false);
    };
  }, [language, activeZoneId]);

  // High-Clarity Multilingual Browser Speech Synthesis
  const handleSpeak = () => {
    if (isPlayingAudio) {
      stopDisasterAudio();
      setIsPlayingAudio(false);
      return;
    }

    const actionHeader = langKey === 'hi'
      ? 'तात्कालिक आपदा निवारक कदम:'
      : langKey === 'as'
      ? 'তাৎক্ষণিক সুৰক্ষা আৰু উদ্ধাৰৰ পদক্ষেপ:'
      : langKey === 'kha'
      ? 'কি লাদ জিংয়াদা বা দেই বান শিম মাৰদৰ:'
      : langKey === 'grt'
      ? 'জা·কু দে·না নাংআনি কামৰাং:'
      : 'Preventive ctions:';
    const speechText = `${content.location}. ${content.tier}. ${content.summary}. ${content.trigger}. ${actionHeader} ${content.actions.join('. ')}`;

    speakDisasterAudio({
      text: speechText,
      language: langKey,
      onStart: () => setIsPlayingAudio(true),
      onEnd: () => setIsPlayingAudio(false),
      onError: () => setIsPlayingAudio(false)
    });
  };

  const getHeaderTitle = () => {
    switch (langKey) {
      case 'kha': return "কা জিংবাতাই শাফাং কা জিংমা & কি লাদ জিংয়াদা (খাসী)";
      case 'grt': return "কেনানি অবস্থা আৰো জা·কু দে·আনি কবোৰ (গাৰো)";
      case 'hi': return "स्थानीय भाषा आपदा पूर्व चेतावनी एवं कार्य योजना (हिन्दी)";
      case 'as': return "স্থানীয় ভাষাৰ জৰুৰী সতৰ্কবাণী আৰু নিৰ্দেশনা (অসমীয়া)";
      default: return "Live Native Language Disaster AAdvisory & ction Plan";
    }
  };

  return (
    <div className="bg-white border-2 border-black p-4 space-y-3">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-black pb-2.5">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 bg-red-600 rounded-full animate-ping inline-block"></span>
          <h3 className="text-sm sm:text-base font-black text-black tracking-tight uppercase">
            {getHeaderTitle()}
          </h3>
        </div>

          <div className="flex items-center gap-2">
            {/* Text-To-Speech AAudio Button (hidden for Khasi/Garo - no native TTS suApport) */}
            {langKey !== 'kha' && langKey !== 'grt' && (
              <button
                type="button"
                onClick={handleSpeak}
                className={`px-3 py-1 text-xs font-mono font-bold border border-black cursor-pointer transition-colors flex items-center gap-1.5 ${
                  isPlayingAudio
                    ? 'bg-red-600 text-white animate-pulse'
                    : 'bg-gray-100 hover:bg-black hover:text-white text-black'
                }`}
                title="Listen to verbal audio alert in local dialect"
              >
                <span>{isPlayingAudio ? ' Stop Audio' : ' Listen Verbal Alert'}</span>
              </button>
            )}

            <span className={`px-2.5 py-0.5 text-xs font-mono font-black uppercase ${content.badgeColor}`}>
              {content.tier}
            </span>
          </div>
      </div>

      {/* Target Location Banner */}
      <div className="bg-gray-50 border border-black p-2.5 text-xs font-mono flex flex-wrap items-center justify-between gap-2">
        <div>
          <span className="text-gray-500 font-bold uppercase text-[10px] block">
            {langKey === 'kha' ? 'জাকা বা দন হা কা জিংমা:' : langKey === 'grt' ? 'কেনানি বিয়াপ:' : langKey === 'hi' ? 'संवेदनशील क्षेत्र:' : langKey === 'as' ? 'বিপদজনক অঞ্চল:' : 'Monitored Sector:'}
          </span>
          <span className="font-black text-black text-sm">{content.location}</span>
        </div>
        <div className="text-right">
          <span className="text-gray-500 font-bold uppercase text-[10px] block">
            {langKey === 'kha' ? 'বোৰ I & চেটেলাইট:' : langKey === 'grt' ? 'চেটেলাইট InSAR:' : 'Telemetry Source:'}
          </span>
          <span className="font-bold text-gray-800">Open-Meteo • Sentinel-1 InSAR • Infinite Slope FS</span>
        </div>
      </div>

      {/* Geotechnical & Physical Diagnosis */}
      <div className="space-y-1.5">
        <h4 className="text-xs font-mono font-black text-black uppercase tracking-wider flex items-center gap-1.5">
          <span></span>
          <span>{langKey === 'kha' ? 'কা দাও বা ত্বা বাদ কা জিংলং কা খিন্দেউ:' : langKey === 'grt' ? 'আ·আ বেয়ানি আ·সেল:' : langKey === 'hi' ? 'भू-तकनीकी एवं उपग्रह विश्लेषण:' : langKey === 'as' ? 'মাটি খহাৰ ভৌতিক কাৰণ:' : 'Physical & Geotechnical Diagnosis:'}</span>
        </h4>
        <p className="text-xs sm:text-sm text-gray-900 leading-relaxed font-sans bg-gray-50/70 p-3 border-l-4 border-black">
          {content.summary}
        </p>
      </div>

      {/* Rainfall Threshold Trigger Forecast */}
      <div className="space-y-1.5 bg-yellow-50/60 border border-yellow-400 p-3">
        <h4 className="text-xs font-mono font-black text-yellow-900 uppercase tracking-wider flex items-center gap-1.5">
          <span>️</span>
          <span>{langKey === 'kha' ? 'উ স্লাপ উ বান পিন-ত্বা য়া উ লুম:' : langKey === 'grt' ? 'মিক্কা দাল·এ বে·আতগিপা:' : langKey === 'hi' ? 'संभावित भूस्खलन ट्रिगर (वर्षा सीमा):' : langKey === 'as' ? 'ভূমিস্খলনৰ সম্ভাৱ্য কাৰক (বৰষুণ):' : 'Precipitation Failure Trigger Forecast:'}</span>
        </h4>
        <p className="text-xs sm:text-sm text-yellow-950 font-semibold leading-relaxed">
          {content.trigger}
        </p>
      </div>

      {/* Immediate Preventive ction Protocols */}
      <div className="space-y-1.5">
        <h4 className="text-xs font-mono font-black text-black uppercase tracking-wider flex items-center gap-1.5">
          <span>️</span>
          <span>{langKey === 'kha' ? 'কি লাদ জিংয়াদা বা দেই বান শিম মাৰদৰ:' : langKey === 'grt' ? 'জা·কু দে·না নাংআনি কামৰাং:' : langKey === 'hi' ? 'तात्कालिक आपदा निवारक कदम:' : langKey === 'as' ? 'তাৎক্ষণিক সুৰক্ষা আৰু উদ্ধাৰৰ পদক্ষেপ:' : 'Immediate Preventive ction Protocols:'}</span>
        </h4>
        <ul className="space-y-1.5 text-xs text-black font-medium">
          {content.actions.map((action, idx) => (
            <li key={`action-${idx}`} className="flex items-start gap-2 bg-gray-50 p-2 border border-gray-200">
              <span className="bg-black text-white font-mono font-bold text-[10px] w-5 h-5 flex items-center justify-center shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <span className="leading-snug">{action}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
