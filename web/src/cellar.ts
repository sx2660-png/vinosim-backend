export type CellarWine = {
  id: string;
  name: string;
  grape: string;
  region: string;
  year: string;
  date: string;
  notes: string;
  rating: number;
};

const KEY = "wine_records";

export function loadCellar(): CellarWine[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as CellarWine[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveCellar(wines: CellarWine[]) {
  localStorage.setItem(KEY, JSON.stringify(wines));
}
