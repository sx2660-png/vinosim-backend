import { NavLink, Route, Routes } from "react-router-dom";
import { CellarPage } from "./pages/Cellar";
import { HomePage } from "./pages/Home";
import { QuizPage } from "./pages/Quiz";
import { StudyPage } from "./pages/Study";
import { TutorPage } from "./pages/Tutor";

const links = [
  ["/", "Home", HomeIcon],
  ["/study", "Study", BookIcon],
  ["/quiz", "Quiz", QuizIcon],
  ["/tutor", "Tutor", ChatIcon],
  ["/cellar", "Cellar", GlassIcon],
] as const;

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 4.5h9.5A3.5 3.5 0 0 1 18 8v11.5H8A3 3 0 0 0 5 16.5v-12Z" />
      <path d="M8 19.5h10" />
    </svg>
  );
}

function QuizIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8" />
      <path d="M9.5 9.5a2.5 2.5 0 1 1 3.2 2.4c-.7.3-1.2.9-1.2 1.6V14" />
      <path d="M12 17h.01" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 6.5h12a1 1 0 0 1 1 1V15a1 1 0 0 1-1 1H10l-4 3v-3H6a1 1 0 0 1-1-1V7.5a1 1 0 0 1 1-1Z" />
    </svg>
  );
}

function GlassIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 3.5h8l-1 8a3 3 0 0 1-6 0l-1-8Z" />
      <path d="M12 14.5V20M9 20h6" />
    </svg>
  );
}

export function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/study" element={<StudyPage />} />
        <Route path="/quiz" element={<QuizPage />} />
        <Route path="/tutor" element={<TutorPage />} />
        <Route path="/cellar" element={<CellarPage />} />
      </Routes>
      <nav className="nav">
        {links.map(([to, label, Icon]) => (
          <NavLink key={to} to={to} end={to === "/"}>
            <Icon />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
