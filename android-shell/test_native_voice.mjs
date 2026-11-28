import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(new URL("./app/src/main/assets/native-voice.js", import.meta.url), "utf8");
function fixture(tag = "TEXTAREA") {
  class TextArea {
    constructor() { this.tagName = tag; this.disabled = false; this.readOnly = false;
      this.isConnected = true; this._value = ""; this.events = []; }
    get value() { return this._value; }
    set value(v) { this._value = v; }
    dispatchEvent(event) { this.events.push(event.type); }
  }
  const field = new TextArea();
  const document = { activeElement: field };
  field.ownerDocument = document;
  const window = {}; window.top = window; window.self = window;
  const location = { href: "https://wrenchrelayllc.com/" };
  const context = vm.createContext({ window, document, location, HTMLTextAreaElement: TextArea,
    Event: class { constructor(type) { this.type = type; } } });
  vm.runInContext(source, context);
  return { field, document, window, location, api: window.__wrNativeVoice };
}
test("append reviewed speech once using the native textarea setter and input events", () => {
  const f = fixture(); f.field.value = "Existing evidence";
  assert.equal(f.api.capture(), true);
  assert.equal(f.api.apply("  Inspected pump  "), true);
  assert.equal(f.field.value, "Existing evidence\nInspected pump");
  assert.deepEqual(f.field.events, ["input", "change"]);
  assert.equal(f.api.apply("Duplicate"), false);
});
test("never write into account/password inputs or disabled/readonly fields", () => {
  assert.equal(fixture("INPUT").api.capture(), false);
  for (const key of ["disabled", "readOnly"]) {
    const f = fixture(); f.field[key] = true; assert.equal(f.api.capture(), false);
  }
});
test("reject changed page, removed field, foreign document and iframe", () => {
  let f = fixture(); f.api.capture(); f.location.href += "different"; assert.equal(f.api.apply("no"), false);
  f = fixture(); f.api.capture(); f.field.isConnected = false; assert.equal(f.api.apply("no"), false);
  f = fixture(); f.api.capture(); f.field.ownerDocument = {}; assert.equal(f.api.apply("no"), false);
  f = fixture(); f.window.top = {}; assert.equal(f.api.capture(), false);
});
test("recognized text is data; JavaScript and HTML characters stay literal", () => {
  const f = fixture(); const text = "'; alert(1); <script>not code</script>";
  f.api.capture(); assert.equal(f.api.apply(text), true); assert.equal(f.field.value, text);
});
