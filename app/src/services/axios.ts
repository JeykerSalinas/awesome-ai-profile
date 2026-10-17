// services/api.ts
import axios from "axios";
import { apiBaseUrl } from "@/config/profile";

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 5000,
});

export default api
