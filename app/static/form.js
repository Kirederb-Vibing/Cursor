function syncChargeFields() {
  const rule = document.getElementById("charge_rule");
  const cadence = document.getElementById("cadence");
  const dayWrap = document.getElementById("day_wrap");
  const anchorWrap = document.getElementById("anchor_wrap");
  if (!rule || !cadence || !dayWrap || !anchorWrap) return;
  dayWrap.style.display = rule.value === "day_of_month" ? "" : "none";
  anchorWrap.style.display = cadence.value === "monthly" ? "none" : "";
}

["charge_rule", "cadence"].forEach((id) => {
  const el = document.getElementById(id);
  if (el) el.addEventListener("change", syncChargeFields);
});
syncChargeFields();
