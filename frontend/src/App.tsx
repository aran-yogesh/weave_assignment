import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "./lib/theme";
import { Home } from "./pages/Home";
import { EngineerDetail } from "./pages/EngineerDetail";

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/engineer/:login" element={<EngineerDetail />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
