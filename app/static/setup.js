document.querySelectorAll("[data-pwd]").forEach((box) => {
  const wrap = document.getElementById(box.getAttribute("data-pwd"));
  if (!wrap) return;
  const input = wrap.querySelector("input");
  const sync = () => {
    wrap.hidden = !box.checked;
    if (input) input.required = box.checked;
    if (!box.checked && input) input.value = "";
  };
  box.addEventListener("change", sync);
  sync();
});
