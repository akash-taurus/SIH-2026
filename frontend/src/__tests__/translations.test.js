import { translations } from '../utils/translations';

describe('Multilingual Translation Dictionary Verification (5 Regional Languages)', () => {
  const languages = ['en', 'hi', 'as', 'kha', 'grt'];
  const requiredKeys = [
    'title',
    'risk_summary_title',
    'risk_low',
    'risk_moderate',
    'risk_high',
    'risk_severe',
    'road_status_title',
    'weather_chart_title',
    'report_button',
    'report_modal_title',
    'submit',
    'cancel'
  ];

  languages.forEach((lang) => {
    test(`language "${lang}" contains all essential translation keys`, () => {
      expect(translations[lang]).toBeDefined();
      requiredKeys.forEach((key) => {
        expect(translations[lang][key]).toBeDefined();
        expect(typeof translations[lang][key]).toBe('string');
        expect(translations[lang][key].length).toBeGreaterThan(0);
      });
    });
  });
});
