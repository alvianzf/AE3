// Material Web components used by login.html (specs/v3/15-design-system.md).
// Imported per-page, not globally, so a page only ships what it uses.
import "@material/web/textfield/outlined-text-field.js";
import "@material/web/button/filled-button.js";
import "@material/web/iconbutton/icon-button.js";
import "@material/web/icon/icon.js";

// md-icon-button's native `toggle` state (visibility / visibility_off icon
// slots already declared in the HTML) replaces shared.js's
// wirePasswordToggles() DOM-walk for any field migrated to this component —
// that helper only ever matched plain <input type=password>, so a migrated
// page drops out of its scope automatically, no coordination needed.
document.querySelectorAll("md-outlined-text-field[type=password]").forEach((field) => {
  const toggleBtn = field.querySelector("md-icon-button[toggle]");
  if (!toggleBtn) return;
  toggleBtn.addEventListener("click", () => {
    field.type = toggleBtn.selected ? "text" : "password";
  });
});
