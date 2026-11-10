import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./console/Layout";
import { Login } from "./console/Login";
import { MonitoringPage, QueuePage } from "./console/Queue";
import { TodayPage } from "./console/Today";
import { WorkspacePage } from "./console/Workspace";
import { ApplyPage } from "./portal/Apply";
import { UploadPage } from "./portal/Upload";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/apply" element={<ApplyPage />} />
        <Route path="/upload/:token" element={<UploadPage />} />
        <Route element={<Layout />}>
          <Route index element={<TodayPage />} />
          <Route path="/queue" element={<QueuePage />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
          <Route path="/m/:id" element={<WorkspacePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
