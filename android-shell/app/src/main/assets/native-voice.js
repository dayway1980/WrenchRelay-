(function () {
  "use strict";
  let target = null;
  let page = null;
  let capturedValue = null;
  function allowed(element) {
    return element && element.tagName === "TEXTAREA" && !element.disabled
      && !element.readOnly && element.ownerDocument === document && element.isConnected;
  }
  window.__wrNativeVoice = {
    capture: function () {
      target = null;
      page = null;
      capturedValue = null;
      if (window.top !== window.self || !allowed(document.activeElement)) return false;
      target = document.activeElement;
      page = location.href;
      capturedValue = target.value;
      return true;
    },
    apply: function (text) {
      const field = target;
      target = null;
      if (!allowed(field) || field.value !== capturedValue || page !== location.href || typeof text !== "string" || !text.trim()) return false;
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
      const value = field.value ? field.value + "\n" + text.trim() : text.trim();
      setter.call(field, value);
      field.dispatchEvent(new Event("input", { bubbles: true }));
      field.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
  };
}());
