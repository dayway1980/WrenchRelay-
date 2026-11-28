(function () {
  "use strict";
  let target = null;
  let page = null;
  function allowed(element) {
    return element && element.tagName === "TEXTAREA" && !element.disabled
      && !element.readOnly && element.ownerDocument === document && element.isConnected;
  }
  window.__wrNativeVoice = {
    capture: function () {
      target = null;
      page = null;
      if (window.top !== window.self || !allowed(document.activeElement)) return false;
      target = document.activeElement;
      page = location.href;
      return true;
    },
    apply: function (text) {
      const field = target;
      target = null;
      if (!allowed(field) || page !== location.href || typeof text !== "string" || !text.trim()) return false;
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
      const value = field.value ? field.value + "\n" + text.trim() : text.trim();
      setter.call(field, value);
      field.dispatchEvent(new Event("input", { bubbles: true }));
      field.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
  };
}());
