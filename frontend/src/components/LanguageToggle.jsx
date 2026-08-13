import { useState } from "react";
import { Button } from "@/components/ui/button";

const LANGS = [
  { code: "en", label: "EN" },
  { code: "es", label: "ES" },
];

export default function LanguageToggle({ onChange }) {
  const [lang, setLang] = useState("en");

  const toggle = () => {
    const next = lang === "en" ? "es" : "en";
    setLang(next);
    onChange?.(next);
  };

  return (
    <Button variant="ghost" size="sm" onClick={toggle} className="text-xs font-mono">
      {LANGS.find((l) => l.code === lang)?.label}
    </Button>
  );
}

// Supports English and Spanish.
// Could be extended to more languages in future releases.
// Fires onChange callback with the new language code.
// Stateless from parent perspective unless controlled.
// Minimal footprint — no i18n library dependency.
