import { NavLink, Route, Routes } from "react-router-dom";
import { CellarPage } from "./pages/Cellar";
import { HomePage } from "./pages/Home";
import { QuizPage } from "./pages/Quiz";
import { StudyPage } from "./pages/Study";
import { TutorPage } from "./pages/Tutor";

const links = [
  ["/", "Home"],
  ["/study", "Study"],
  ["/quiz", "Quiz"],
  ["/tutor", "Tutor"],
  ["/cellar", "Cellar"],
] as const;

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
        {links.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/"}>
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
