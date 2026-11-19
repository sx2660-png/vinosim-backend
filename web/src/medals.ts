export function medalName(id: string): string {
  if (id === "level1") return "Level 1 medal · Foundations of Tasting";
  if (id === "level2") return "Level 2 medal · Grapes, Regions and Labels";
  if (id.startsWith("bonus:")) return "Bonus medal";
  return "Medal";
}

// Any screen that gets new_medals back from the API calls this; App shows the toast.
export function announceMedals(ids: string[] | undefined) {
  if (!ids || ids.length === 0) return;
  window.dispatchEvent(new CustomEvent("vinosim:medals", { detail: ids }));
}
