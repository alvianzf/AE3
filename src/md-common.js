// Shared across every MD3-migrated page (specs/v3/15-design-system.md).
// Component imports pages actually use pull this in too, so a page's own
// entry only needs to import the components its markup doesn't already
// cover via this shared module.
import "@material/web/textfield/outlined-text-field.js";
import "@material/web/button/filled-button.js";
import "@material/web/button/outlined-button.js";
import "@material/web/button/text-button.js";
import "@material/web/iconbutton/icon-button.js";
import "@material/web/icon/icon.js";

// md-icon-button's native `toggle` state (visibility / visibility_off icon
// slots declared in the HTML) replaces shared.js's wirePasswordToggles()
// DOM-walk for any field migrated to md-outlined-text-field — that helper
// only ever matched plain <input type=password>, so a migrated page drops
// out of its scope automatically, no coordination needed between the two.
export function wireMdPasswordToggles() {
  document.querySelectorAll("md-outlined-text-field[type=password]").forEach((field) => {
    const toggleBtn = field.querySelector("md-icon-button[toggle]");
    if (!toggleBtn) return;
    toggleBtn.addEventListener("click", () => {
      field.type = toggleBtn.selected ? "text" : "password";
    });
  });
}
