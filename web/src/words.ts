import type { SheetLine } from "./api";

// Three-part cards: what you feel → the word people use → one reason it happens.
export const STRUCTURE_CARDS = [
  {
    word: "Acidity",
    feel: "Your mouth waters. It tastes fresh or sharp, like biting a green apple.",
    why: "Grapes lose acid as they ripen, so wines from cooler places usually keep more of it.",
  },
  {
    word: "Tannin",
    feel: "Your gums and the inside of your cheeks feel dry, tight or a little rough.",
    why: "It comes from grape skins, seeds and stems (and some from oak). Red wine sits on its skins, so it has more.",
  },
  {
    word: "Body",
    feel: "The weight of the wine in your mouth: light like water, or heavier like milk.",
    why: "Mostly from alcohol. Riper grapes from warmer places make more alcohol, so the wine feels fuller.",
  },
  {
    word: "Sweetness",
    feel: "A sugary, sometimes sticky feel on the tip of your tongue.",
    why: "Sugar that was left when fermentation stopped before all of it turned into alcohol.",
  },
  {
    word: "Alcohol",
    feel: "Warmth at the back of your throat or in your chest after you swallow.",
    why: "Yeast turns grape sugar into alcohol, so riper, sweeter grapes give stronger wine.",
  },
];

export const SHEET_LINES: { key: SheetLine; step: string; title: string; ask: string; common: string }[] = [
  {
    key: "appearance",
    step: "Look",
    title: "Appearance",
    ask: "What colour is it, and how deep does it look?",
    common: "pale · medium · deep — lemon, gold, pink, ruby, garnet",
  },
  {
    key: "nose",
    step: "Smell",
    title: "Nose",
    ask: "What does it smell like to you? There is no wrong answer.",
    common: "fruit (cherry, citrus, apple), flowers, spice, vanilla or toast from oak, earth",
  },
  {
    key: "palate",
    step: "Taste",
    title: "Palate",
    ask: "How does it feel in your mouth? Use one word and say what you felt.",
    common: "acidity = mouth-watering · tannin = gums feel dry · body = light or heavy · sweetness · alcohol = warmth",
  },
  {
    key: "liking",
    step: "Like it?",
    title: "Do you like it?",
    ask: "Would you drink it again? Why or why not?",
    common: "easy to drink · a bit sharp for me · would be good with food — no wrong answer",
  },
];

export const MISSING_TEXT: Record<string, string> = {
  appearance: "Write a few words about how it looks.",
  nose: "Write what you smell, in any words.",
  palate: "Write how it feels in your mouth.",
  liking: "Say whether you like it.",
  palate_structure_word: "On the palate line, try one word: acidity, tannin, body, sweetness or alcohol.",
  palate_sensation: "Say what you felt that made you pick that word, or fill in “because”.",
};
