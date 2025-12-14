import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue } from
'@/components/ui/select';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

const languages = [
{ code: 'en', name: 'English' },
{ code: 'es', name: 'Español' },
{ code: 'fr', name: 'Français' },
{ code: 'de', name: 'Deutsch' }];


export function LanguageSelector() {
  const { i18n } = useTranslation();

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng);
    localStorage.setItem('mbse-language', lng);
  };

  return (/*#__PURE__*/
    _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
      _jsx(Globe, { className: "h-4 w-4 text-muted-foreground" }), /*#__PURE__*/
      _jsxs(Select, { value: i18n.language, onValueChange: changeLanguage, children: [/*#__PURE__*/
        _jsx(SelectTrigger, { className: "w-[140px]", children: /*#__PURE__*/
          _jsx(SelectValue, { placeholder: "Select language" }) }
        ), /*#__PURE__*/
        _jsx(SelectContent, { children:
          languages.map((lang) => /*#__PURE__*/
          _jsx(SelectItem, { value: lang.code, children:
            lang.name }, lang.code
          )
          ) }
        )] }
      )] }
    ));

}

export default LanguageSelector;
