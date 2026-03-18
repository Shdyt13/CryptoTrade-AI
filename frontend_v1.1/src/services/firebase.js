import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

// ⚠️ PENTING: Ganti kode di bawah ini dengan Config asli dari Firebase Console Anda!
// (Config yang sama dengan yang ada di serviceAccountKey, tapi versi web)
// Kalau bingung, pakai config yang ini dulu (tapi nanti harus diganti biar jalan):

const firebaseConfig = {
  apiKey: "AIzaSyCATbiyGmt5pf3prLFdGuYH6g0LlLlaUuU",
  authDomain: "eth-predictor-sapar.firebaseapp.com",
  projectId: "eth-predictor-sapar",
  storageBucket: "eth-predictor-sapar.firebasestorage.app",
  messagingSenderId: "583489789404",
  appId: "1:583489789404:web:a80fdbc3ac562baa1f8319"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

export { db };