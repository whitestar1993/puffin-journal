export const MOODS = [
  { value: 1, emoji: "😞", label: "Awful" },
  { value: 2, emoji: "😕", label: "Low" },
  { value: 3, emoji: "😐", label: "Okay" },
  { value: 4, emoji: "🙂", label: "Good" },
  { value: 5, emoji: "😄", label: "Great" },
];

export const moodEmoji = (v: number) => MOODS[v - 1]?.emoji ?? "·";
export const moodLabel = (v: number) => MOODS[v - 1]?.label ?? "";
