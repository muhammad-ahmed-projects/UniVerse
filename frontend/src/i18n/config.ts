import i18n from "i18next";
import ICU from "i18next-icu";
import resourcesToBackend from "i18next-resources-to-backend";
import { initReactI18next } from "react-i18next";

import { isLocale, isRtl, routing } from "./routing";

const syncDocument = (lng: string) => {
  const locale = isLocale(lng) ? lng : routing.defaultLocale;
  document.documentElement.lang = locale;
  document.documentElement.dir = isRtl(locale) ? "rtl" : "ltr";
};

i18n.on("languageChanged", syncDocument);

// The dashboard is English-only: only en.json has the UniVerse strings, and
// the language picker was removed. No browser-language detection, so a
// German/Arabic browser doesn't get a half-translated (or right-to-left) UI.
i18n
  .use(ICU)
  .use(
    // Vite code-splits one chunk per locale JSON.
    resourcesToBackend((lng: string) => import(`../messages/${lng}.json`)),
  )
  .use(initReactI18next)
  .init({
    lng: routing.defaultLocale,
    supportedLngs: [routing.defaultLocale],
    fallbackLng: routing.defaultLocale,
    load: "languageOnly", // "en-US" -> "en"
    ns: ["translation"],
    defaultNS: "translation",
    keySeparator: ".",
    nsSeparator: false, // keys/values may contain ":"
    returnNull: false,
    returnObjects: false,
    interpolation: { escapeValue: false }, // React already escapes
    react: { useSuspense: true },
  });

export default i18n;
