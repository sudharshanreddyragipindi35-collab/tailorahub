import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import AlertTriangle from "lucide-react/dist/esm/icons/alert-triangle.js";
import ArrowRight from "lucide-react/dist/esm/icons/arrow-right.js";
import BadgeCheck from "lucide-react/dist/esm/icons/badge-check.js";
import Ban from "lucide-react/dist/esm/icons/ban.js";
import Bell from "lucide-react/dist/esm/icons/bell.js";
import ChevronLeft from "lucide-react/dist/esm/icons/chevron-left.js";
import CheckCircle2 from "lucide-react/dist/esm/icons/check-circle-2.js";
import ClipboardList from "lucide-react/dist/esm/icons/clipboard-list.js";
import Crown from "lucide-react/dist/esm/icons/crown.js";
import CreditCard from "lucide-react/dist/esm/icons/credit-card.js";
import FileClock from "lucide-react/dist/esm/icons/file-clock.js";
import Globe2 from "lucide-react/dist/esm/icons/globe-2.js";
import Heart from "lucide-react/dist/esm/icons/heart.js";
import ImageIcon from "lucide-react/dist/esm/icons/image.js";
import LayoutDashboard from "lucide-react/dist/esm/icons/layout-dashboard.js";
import LogOut from "lucide-react/dist/esm/icons/log-out.js";
import Megaphone from "lucide-react/dist/esm/icons/megaphone.js";
import Moon from "lucide-react/dist/esm/icons/moon.js";
import Pencil from "lucide-react/dist/esm/icons/pencil.js";
import RefreshCw from "lucide-react/dist/esm/icons/refresh-cw.js";
import Scissors from "lucide-react/dist/esm/icons/scissors.js";
import Search from "lucide-react/dist/esm/icons/search.js";
import Shield from "lucide-react/dist/esm/icons/shield.js";
import Star from "lucide-react/dist/esm/icons/star.js";
import Sun from "lucide-react/dist/esm/icons/sun.js";
import Tag from "lucide-react/dist/esm/icons/tag.js";
import Trash2 from "lucide-react/dist/esm/icons/trash-2.js";
import UploadCloud from "lucide-react/dist/esm/icons/upload-cloud.js";
import UsersRound from "lucide-react/dist/esm/icons/users-round.js";
import Video from "lucide-react/dist/esm/icons/video.js";
import XCircle from "lucide-react/dist/esm/icons/x-circle.js";
import { api, assetUrl, clearSession, getRole, getToken, hasValidStoredSession, isSessionExpired, markSessionActive, setSession } from "./api";
import MapPicker from "./components/MapPicker";
import { registerPwa } from "./registerPwa";
import "./styles.css";

const roles = [
  ["customer", "Customer", UsersRound, "Discover approved ateliers, book appointments, track orders and pay securely."],
  ["tailor", "Tailor", Scissors, "Manage your profile, availability, services, requests, orders and earnings."],
  ["admin", "Admin", Shield, "Approve tailors, review operations and manage the TailoraHub platform."],
];

const languageOptions = [
  ["en", "English", "EN"],
  ["te", "తెలుగు", "TE"],
];

const translations = {
  te: {
    "common.language": "భాష",
    "common.refresh": "రిఫ్రెష్",
    "common.logout": "లాగ్ అవుట్",
    "common.loading": "లోడ్ అవుతోంది...",
    "common.pleaseWait": "దయచేసి వేచి ఉండండి...",
    "common.login": "లాగిన్",
    "common.register": "నమోదు",
    "common.password": "పాస్‌వర్డ్",
    "common.otp": "OTP",
    "common.back": "వెనక్కి",
    "common.continue": "కొనసాగించు",
    "common.apply": "అప్లై",
    "common.support": "సపోర్ట్",
    "common.wallet": "వాలెట్",
    "common.referrals": "రిఫరల్స్",
    "common.requests": "అభ్యర్థనలు",
    "common.orders": "ఆర్డర్లు",
    "common.updates": "అప్‌డేట్స్",
    "common.favorites": "ఫేవరెట్స్",
    "common.services": "సేవలు",
    "common.offers": "ఆఫర్లు",
    "common.followers": "ఫాలోవర్స్",
    "common.availability": "అందుబాటు",
    "common.overview": "ఓవర్వ్యూ",
    "common.photosVideos": "ఫోటోలు / వీడియోలు",
    "common.waitingList": "వెయిటింగ్ లిస్ట్",
    "common.search": "సెర్చ్",
    "common.roles": "పాత్రలు",
    "wallet.loading": "వాలెట్ లోడ్ అవుతోంది...",
    "referrals.loading": "రిఫరల్స్ లోడ్ అవుతున్నాయి...",
    "referrals.shareableLink": "షేర్ చేయగల లింక్",
    "common.available": "అందుబాటులో ఉంది",
    "common.fewSlots": "కొన్ని స్లాట్లు మాత్రమే",
    "common.busy": "బిజీ",
    "common.unavailable": "అందుబాటులో లేదు",
    "role.customer.label": "కస్టమర్",
    "role.customer.description": "ఆమోదించిన టైలర్లను చూసి, బుకింగ్‌లు చేసి, ఆర్డర్లను ట్రాక్ చేసి, సురక్షితంగా చెల్లించండి.",
    "role.tailor.label": "టైలర్",
    "role.tailor.description": "మీ ప్రొఫైల్, అందుబాటు, సేవలు, అభ్యర్థనలు, ఆర్డర్లు మరియు ఆదాయాన్ని నిర్వహించండి.",
    "role.admin.label": "అడ్మిన్",
    "role.admin.description": "టైలర్లను ఆమోదించండి, ఆపరేషన్లను పరిశీలించండి మరియు TailoraHub ప్లాట్‌ఫారమ్‌ను నిర్వహించండి.",
    "home.tagline": "స్టైల్‌కు పరిపూర్ణత కలిసే స్థలం",
    "home.chooseRole": "పాత్రను ఎంచుకోండి",
    "home.verifiedTailors": "ధృవీకరించిన టైలర్లు",
    "home.securePayments": "సురక్షిత చెల్లింపులు",
    "home.premiumExperience": "ప్రీమియం అనుభవం",
    "auth.atelier": "TailoraHub అటెలియర్",
    "auth.accessTitle": "{role} యాక్సెస్",
    "auth.roleSelection": "పాత్ర ఎంపిక",
    "auth.loginSubtitle": "{role} లాగిన్",
    "auth.registrationSubtitle": "{role} నమోదు",
    "auth.passwordMode": "పాస్‌వర్డ్",
    "auth.otpMode": "OTP",
    "auth.forgotPassword": "పాస్‌వర్డ్ మర్చిపోయారా?",
    "auth.usernameOrMobile": "యూజర్‌నేమ్ లేదా మొబైల్ నంబర్",
    "auth.mobileOrEmail": "మొబైల్ నంబర్ లేదా ఇమెయిల్",
    "auth.adminIdentifier": "అడ్మిన్ యూజర్‌నేమ్ లేదా ఇమెయిల్",
    "auth.emailOtp": "ఇమెయిల్ OTP",
    "auth.sendOtp": "OTP పంపండి",
    "auth.verifyOtp": "OTP ధృవీకరించండి",
    "auth.otpCode": "OTP కోడ్",
    "auth.sendLoginOtp": "లాగిన్ OTP పంపండి",
    "auth.verifyOtpLogin": "OTP ధృవీకరించి లాగిన్ చేయండి",
    "auth.loginAs": "{role}గా లాగిన్ చేయండి",
    "auth.createAccount": "{role} ఖాతా సృష్టించండి",
    "auth.createTailor": "టైలర్ ఖాతా సృష్టించండి",
    "auth.createCustomer": "కస్టమర్ ఖాతా సృష్టించండి",
    "auth.resetCustomer": "కస్టమర్ పాస్‌వర్డ్ రీసెట్",
    "auth.resetTailor": "టైలర్ పాస్‌వర్డ్ రీసెట్",
    "auth.backToLogin": "లాగిన్‌కు తిరిగి వెళ్ళండి",
    "auth.sendResetOtp": "రీసెట్ OTP పంపండి",
    "auth.resetPassword": "పాస్‌వర్డ్ రీసెట్",
    "auth.newPassword": "కొత్త పాస్‌వర్డ్",
    "auth.confirmNewPassword": "కొత్త పాస్‌వర్డ్ నిర్ధారించండి",
    "auth.fullName": "పూర్తి పేరు",
    "auth.emailOptional": "ఇమెయిల్ (ఐచ్ఛికం)",
    "auth.mobileNumber": "మొబైల్ నంబర్",
    "auth.sixDigitOtp": "6 అంకెల OTP",
    "auth.confirmPassword": "పాస్‌వర్డ్ నిర్ధారించండి",
    "auth.strongPassword": "బలమైన పాస్‌వర్డ్",
    "auth.passwordHint": "8+ అక్షరాలు, అక్షరాలు మరియు సంఖ్యలు ఉపయోగించండి",
    "auth.referralOptional": "రిఫరల్ కోడ్ (ఐచ్ఛికం)",
    "auth.customerTerms": "TailoraHub నిబంధనలు & షరతులను నేను అంగీకరిస్తున్నాను.",
    "wizard.Aadhaar": "ఆధార్",
    "wizard.Mobile": "మొబైల్",
    "wizard.Email": "ఇమెయిల్",
    "wizard.Experience": "అనుభవం",
    "wizard.Password": "పాస్‌వర్డ్",
    "wizard.Terms": "నిబంధనలు",
    "wizard.Location": "లొకేషన్",
    "dashboard.customer.title": "కస్టమర్ డాష్‌బోర్డ్",
    "dashboard.customer.subtitle": "ఆమోదించిన టైలర్లను చూసి బుక్ చేయండి",
    "dashboard.tailor.title": "టైలర్ డాష్‌బోర్డ్",
    "dashboard.tailor.subtitle": "అభ్యర్థనలు, ఆర్డర్లు మరియు అందుబాటు",
    "dashboard.admin.title": "అడ్మిన్",
    "dashboard.admin.subtitle": "ప్లాట్‌ఫారమ్ ఆపరేషన్స్",
    "dashboard.platform": "ప్లాట్‌ఫారమ్ డాష్‌బోర్డ్",
    "customer.findTrack": "టైలర్లను కనుగొని ట్రాక్ చేయండి",
    "customer.chooseSection": "కొనసాగడానికి విభాగాన్ని ఎంచుకోండి.",
    "customer.selected": "ఎంపిక",
    "customer.panel.browse": "టైలర్లను చూడండి",
    "customer.panel.profile": "ఎంచుకున్న టైలర్",
    "customer.loading": "కస్టమర్ డేటా లోడ్ అవుతోంది...",
    "customer.nearbySearch": "దగ్గరలోని టైలర్ సెర్చ్",
    "customer.tailorSearch": "టైలర్ సెర్చ్",
    "customer.geo.detecting": "మీ లొకేషన్ గుర్తిస్తోంది...",
    "customer.geo.ready": "మీ ప్రస్తుత లొకేషన్‌కు దగ్గరగా ఉన్న టైలర్లు దూరం ప్రకారం చూపబడతారు.",
    "customer.geo.denied": "లొకేషన్ అనుమతి ఇవ్వలేదు. ఆమోదించిన టైలర్లను చూపిస్తున్నాం.",
    "customer.geo.unavailable": "లొకేషన్ అనుమతి అందుబాటులో లేదు. ఆమోదించిన టైలర్లను చూపిస్తున్నాం.",
    "customer.radius": "రేడియస్ {radius} కిమీ",
    "customer.searchPlaceholder": "టైలర్, లొకేషన్, నైపుణ్యం సెర్చ్ చేయండి",
    "customer.servicePlaceholder": "సేవ",
    "customer.allAvailability": "అన్ని అందుబాటు స్థితులు",
    "customer.nearbyTailors": "దగ్గరలోని టైలర్లు",
    "customer.approvedTailors": "ఆమోదించిన టైలర్లు",
    "customer.noTailors": "ప్రస్తుత ఫిల్టర్లకు సరిపడే టైలర్లు లేరు. ఫిల్టర్లు తొలగించండి లేదా అడ్మిన్‌లో టైలర్‌ను ఆమోదించండి.",
    "customer.selectTailorEmpty": "ప్రొఫైల్, సేవలు, రివ్యూలు, అందుబాటు మరియు బుకింగ్ ఫారమ్ చూడడానికి Browse Tailors నుండి ఒక టైలర్‌ను ఎంచుకోండి.",
    "customer.favoriteTailors": "ఫేవరెట్ టైలర్లు",
    "customer.noFavorites": "ఇంకా ఫేవరెట్ టైలర్లు లేరు. మీకు నచ్చిన టైలర్‌పై హార్ట్ ట్యాప్ చేయండి.",
    "customer.updatesTitle": "కస్టమర్ అప్‌డేట్స్",
    "customer.walletDescription": "రిఫండ్లు మరియు భవిష్యత్ రిఫరల్ క్రెడిట్లు మీ కస్టమర్ ఖాతాలో ఇక్కడ ఉంటాయి.",
    "customer.reservedCredits": "రిజర్వ్ చేసిన క్రెడిట్లు",
    "customer.referralHelp": "కొత్త కస్టమర్ పూర్తిగా కొత్త మొబైల్ నంబర్‌తో నమోదు అయితే మాత్రమే రిఫరల్ చెల్లుబాటు అవుతుంది.",
    "customer.referralCode": "మీ రిఫరల్ కోడ్",
    "customer.validReferrals": "చెల్లుబాటు అయ్యే రిఫరల్స్",
    "customer.addFavorite": "ఫేవరెట్‌గా జోడించండి",
    "customer.removeFavorite": "ఫేవరెట్ నుండి తీసివేయండి",
    "customer.favorited": "ఫేవరెట్",
    "customer.followTailor": "టైలర్‌ను ఫాలో అవ్వండి",
    "customer.unfollow": "ఫాలో తొలగించండి",
    "customer.follow": "ఫాలో",
    "customer.following": "ఫాలో అవుతున్నారు",
    "customer.fromPrice": "ప్రారంభం",
    "customer.distance": "దూరం",
    "customer.experience": "అనుభవం",
    "customer.years": "సంవత్సరాలు",
    "customer.viewProfile": "ప్రొఫైల్ చూడండి",
    "customer.book": "బుక్ చేయండి",
    "tailor.pendingRequests": "పెండింగ్ అభ్యర్థనలు",
    "tailor.activeOrders": "యాక్టివ్ ఆర్డర్లు",
    "tailor.completedOrders": "పూర్తయిన ఆర్డర్లు",
    "tailor.earnings": "ఆదాయం",
    "tailor.currentAvailability": "ప్రస్తుత అందుబాటు",
    "tailor.availableSlots": "అందుబాటులో ఉన్న స్లాట్లు",
    "tailor.nextAvailable": "తదుపరి అందుబాటు",
    "tailor.publicMedia": "పబ్లిక్ మీడియా",
    "tailor.manageMedia": "మీడియా నిర్వహించండి",
    "tailor.followerUpdates": "ఫాలోవర్ అప్‌డేట్స్",
    "tailor.postOffer": "ఆఫర్ పోస్ట్ చేయండి",
    "tailor.noFollowers": "ఇంకా ఫాలోవర్స్ లేరు.",
    "tailor.profilePending": "మీ టైలర్ ప్రొఫైల్ {status}. అడ్మిన్ ఆమోదించిన తర్వాత మాత్రమే కస్టమర్లకు కనిపిస్తుంది.",
    "tailor.loading": "టైలర్ డాష్‌బోర్డ్ లోడ్ అవుతోంది...",
    "tailor.updatesTitle": "టైలర్ అప్‌డేట్స్",
    "tailor.walletDescription": "మీ UPI లేదా బ్యాంక్ వివరాలను కస్టమర్లకు చూపకుండా QR చెల్లింపులు మీ వాలెట్ లెడ్జర్‌కు క్రెడిట్ అవుతాయి.",
    "tailor.upiVisible": "మీకు మరియు అధీకృత అడ్మిన్లకు మాత్రమే కనిపిస్తుంది. కస్టమర్లు QR టోకెన్‌తో చెల్లిస్తారు.",
    "tailor.referralHelp": "మీ కోడ్‌ను ఇతర టైలర్లతో పంచుకోండి. మీ డాష్‌బోర్డ్ నేరుగా మీరు రిఫర్ చేసిన వారినే చూపిస్తుంది.",
    "tailor.youReferred": "మీరు రిఫర్ చేసిన వారు",
    "tailor.status": "స్థితి",
    "tailor.maxNewOrders": "గరిష్ఠ కొత్త ఆర్డర్లు",
    "tailor.nextAvailableDate": "తదుపరి అందుబాటు తేదీ",
    "tailor.acceptingRequests": "కొత్త అభ్యర్థనలు స్వీకరిస్తున్నారు",
    "tailor.availabilityNote": "అందుబాటు గమనిక",
    "tailor.saveAvailability": "అందుబాటు సేవ్ చేయండి",
    "admin.searchPlaceholder": "ప్రస్తుత డేటాలో సెర్చ్ చేయండి",
    "admin.loading": "లైవ్ డేటా లోడ్ అవుతోంది...",
    "admin.dashboard": "డాష్‌బోర్డ్",
    "admin.customers": "కస్టమర్ నిర్వహణ",
    "admin.tailors": "టైలర్ నిర్వహణ",
    "admin.approvals": "టైలర్ ఆమోదాలు",
    "admin.bookingRequests": "బుకింగ్ అభ్యర్థనలు",
    "admin.orderManagement": "ఆర్డర్ నిర్వహణ",
    "admin.paymentManagement": "చెల్లింపు నిర్వహణ",
    "admin.finance": "ఫైనాన్స్ ఇంజిన్",
    "admin.referralTree": "రిఫరల్ ట్రీ",
    "admin.customerReferrals": "కస్టమర్ రిఫరల్స్",
    "admin.disputes": "డిస్ప్యూట్ క్యూ",
    "admin.reviews": "రివ్యూ నిర్వహణ",
    "admin.supportCenter": "సపోర్ట్ సెంటర్",
    "admin.complaints": "ఫిర్యాదు నిర్వహణ",
    "admin.audit": "అడ్మిన్ ఆడిట్ లాగ్స్",
    "status.AVAILABLE": "అందుబాటులో ఉంది",
    "status.FEW_SLOTS_AVAILABLE": "కొన్ని స్లాట్లు మాత్రమే",
    "status.BUSY": "బిజీ",
    "status.NOT_AVAILABLE": "అందుబాటులో లేదు",
    "status.ACTIVE": "యాక్టివ్",
    "status.APPROVED": "ఆమోదించబడింది",
    "status.PENDING_APPROVAL": "ఆమోదం కోసం వేచి ఉంది",
    "status.COMPLETED": "పూర్తయింది",
    "status.PAID": "చెల్లించబడింది",
    "status.RESOLVED": "పరిష్కరించబడింది",
    "availability.AVAILABLE": "కొత్త బుకింగ్ అభ్యర్థనలు సాధారణంగా స్వీకరిస్తున్నారు.",
    "availability.FEW_SLOTS_AVAILABLE": "పరిమిత కొత్త బుకింగ్‌లు మాత్రమే స్వీకరిస్తున్నారు.",
    "availability.BUSY": "పని ఎక్కువగా ఉంది. అయినా అభ్యర్థనలు పంపవచ్చు.",
    "availability.NOT_AVAILABLE": "ప్రస్తుతం కొత్త ఆర్డర్లు స్వీకరించడం లేదు.",
  },
};

function translate(language, key, fallback = key, values = {}) {
  const template = translations[language]?.[key] || fallback;
  return Object.entries(values).reduce((text, [name, value]) => String(text).replaceAll(`{${name}}`, value), template);
}

const LanguageContext = createContext({
  language: "en",
  setLanguage: () => {},
  t: (_key, fallback) => fallback,
});

function useLanguage() {
  return useContext(LanguageContext);
}

function useT() {
  return useLanguage().t;
}

function initialTheme() {
  if (typeof window === "undefined") return "dark";
  return window.localStorage.getItem("tailorahub-theme") === "light" ? "light" : "dark";
}

function initialLanguage() {
  if (typeof window === "undefined") return "en";
  return window.localStorage.getItem("tailorahub-language") || "en";
}

const adminSections = [
  ["dashboard", "Dashboard", Shield],
  ["customers", "Customer Management", UsersRound],
  ["tailors", "Tailor Management", Scissors],
  ["approvals", "Tailor Approvals", BadgeCheck],
  ["requests", "Booking Requests", ClipboardList],
  ["orders", "Order Management", ClipboardList],
  ["payments", "Payment Management", CreditCard],
  ["finance", "Finance Engine", CreditCard],
  ["referrals", "Referral Tree", UsersRound],
  ["customerReferrals", "Customer Referrals", UsersRound],
  ["disputes", "Dispute Queue", AlertTriangle],
  ["reviews", "Review Management", Star],
  ["support", "Support Center", AlertTriangle],
  ["complaints", "Complaint Management", AlertTriangle],
  ["audit", "Admin Audit Logs", FileClock],
];

const adminSectionKeys = {
  dashboard: "admin.dashboard",
  customers: "admin.customers",
  tailors: "admin.tailors",
  approvals: "admin.approvals",
  requests: "admin.bookingRequests",
  orders: "admin.orderManagement",
  payments: "admin.paymentManagement",
  finance: "admin.finance",
  referrals: "admin.referralTree",
  customerReferrals: "admin.customerReferrals",
  disputes: "admin.disputes",
  reviews: "admin.reviews",
  support: "admin.supportCenter",
  complaints: "admin.complaints",
  audit: "admin.audit",
};

function adminSectionLabel(id, fallback, t) {
  return t(adminSectionKeys[id] || `admin.${id}`, fallback);
}

function availabilityMessage(status, t) {
  return t(`availability.${status}`, availabilityCopy[status] || "Availability not updated");
}

const availabilityCopy = {
  AVAILABLE: "Accepting new booking requests normally.",
  FEW_SLOTS_AVAILABLE: "Accepting limited new bookings.",
  BUSY: "High workload. Requests may still be sent.",
  NOT_AVAILABLE: "Currently not accepting new orders.",
};

const trackerSteps = [
  ["MEASUREMENT_SCHEDULED", "Measurement scheduled"],
  ["MEASUREMENT_COMPLETED", "Measurement completed"],
  ["CLOTH_RECEIVED", "Cloth received"],
  ["CUTTING_STARTED", "Cutting started"],
  ["CUTTING_COMPLETED", "Cutting completed"],
  ["STITCHING_STARTED", "Stitching started"],
  ["STITCHING_IN_PROGRESS", "Stitching in progress"],
  ["STITCHING_COMPLETED", "Stitching completed"],
  ["READY_FOR_HANDOVER", "Ready for handover"],
  ["PAYMENT_PENDING", "Payment pending"],
  ["DELIVERY_PENDING", "Delivery pending"],
];

const bookingTrackerStages = [
  "Order Placed",
  "Measurement Scheduled",
  "Measurement Done",
  "Stitching in Progress",
  "Ready for Delivery",
  "Out for Delivery",
  "Delivered",
];

const supportPriorities = ["LOW", "NORMAL", "HIGH", "URGENT"];
const customerSupportCategories = [
  "Booking request",
  "Payment or refund",
  "Measurement / home visit",
  "Order tracking",
  "Delivery or handover",
  "Account or login",
  "Tailor profile concern",
  "Other",
];
const tailorSupportCategories = [
  "Approval / verification",
  "Profile or listing",
  "Booking requests",
  "Order tracker",
  "Payments / earnings",
  "Availability",
  "Media or portfolio",
  "Account or login",
  "Other",
];

function money(value) {
  return `Rs ${Number(value || 0).toLocaleString("en-IN")}`;
}

const TRAVEL_CHARGE_PER_KM = 5;
const BOOKING_TAX_ESTIMATE_PERCENTAGE = 20;

function finiteNumber(value) {
  const next = Number(value);
  return Number.isFinite(next) ? next : null;
}

function distanceKm(lat1, lng1, lat2, lng2) {
  const aLat = finiteNumber(lat1);
  const aLng = finiteNumber(lng1);
  const bLat = finiteNumber(lat2);
  const bLng = finiteNumber(lng2);
  if ([aLat, aLng, bLat, bLng].some((value) => value === null)) return 0;
  const toRad = (value) => (value * Math.PI) / 180;
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const originLat = toRad(aLat);
  const targetLat = toRad(bLat);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(originLat) * Math.cos(targetLat) * Math.sin(dLng / 2) ** 2;
  return Math.round(6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)) * 10) / 10;
}

function estimateTravelDistanceKm(tailor, location) {
  const tailorLat = tailor?.lat ?? tailor?.latitude ?? tailor?.shopLat;
  const tailorLng = tailor?.lng ?? tailor?.longitude ?? tailor?.shopLng;
  const pickedLat = location?.latitude ?? location?.lat;
  const pickedLng = location?.longitude ?? location?.lng;
  const exactDistance = distanceKm(tailorLat, tailorLng, pickedLat, pickedLng);
  if (exactDistance > 0) return exactDistance;
  return finiteNumber(tailor?.distanceKm ?? tailor?.distance_km) || 0;
}

function fmtDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

function fmtDay(value) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("en-IN", { dateStyle: "medium" });
}

function unreadCount(rows = []) {
  return rows.filter((row) => !row.read).length;
}

const APP_HISTORY_KEY = "tailorahub";
const MEASUREMENT_APPOINTMENT_BLOCKED_WINDOW_DAYS = 2;
const MEASUREMENT_APPOINTMENT_ERROR = "Measurement appointment must be scheduled at least 3 days before the delivery date.";

function currentHistoryState() {
  const state = window.history.state;
  return state && typeof state === "object" ? state : {};
}

function readAppHistoryValue(scope, fallback) {
  const appState = currentHistoryState()[APP_HISTORY_KEY];
  return appState && Object.prototype.hasOwnProperty.call(appState, scope) ? appState[scope] : fallback;
}

function writeAppHistoryValue(scope, value, replace = false) {
  const current = currentHistoryState();
  const next = {
    ...current,
    [APP_HISTORY_KEY]: {
      ...(current[APP_HISTORY_KEY] || {}),
      [scope]: value,
    },
  };
  const method = replace ? "replaceState" : "pushState";
  window.history[method](next, "", window.location.href);
}

function useAppHistoryState(scope, initialValue) {
  const [value, setValue] = useState(() => readAppHistoryValue(scope, initialValue));
  const valueRef = useRef(value);

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  useEffect(() => {
    if (!Object.prototype.hasOwnProperty.call(currentHistoryState()[APP_HISTORY_KEY] || {}, scope)) {
      writeAppHistoryValue(scope, valueRef.current, true);
    }
    function handlePopState(event) {
      const appState = event.state?.[APP_HISTORY_KEY];
      const next = appState && Object.prototype.hasOwnProperty.call(appState, scope) ? appState[scope] : initialValue;
      valueRef.current = next;
      setValue(next);
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [scope, initialValue]);

  const navigate = useCallback((nextValue, options = {}) => {
    const resolved = typeof nextValue === "function" ? nextValue(valueRef.current) : nextValue;
    if (Object.is(resolved, valueRef.current)) return;
    valueRef.current = resolved;
    setValue(resolved);
    writeAppHistoryValue(scope, resolved, Boolean(options.replace));
  }, [scope]);

  return [value, navigate];
}

function normalizeReferralCode(value) {
  return String(value || "").trim().toUpperCase().replace(/[^A-Z0-9_-]/g, "");
}

function readReferralEntry() {
  const params = new URLSearchParams(window.location.search);
  const code = normalizeReferralCode(params.get("ref") || params.get("referral") || params.get("referralCode"));
  if (!code) return null;
  const path = window.location.pathname.toLowerCase();
  const roleParam = String(params.get("role") || "").toLowerCase();
  const role = path.includes("/customer/") || roleParam === "customer" ? "customer" : "tailor";
  return { role, code };
}

function clearReferralBrowserUrl() {
  window.history.replaceState(currentHistoryState(), "", "/");
}

function dateInputToUtcDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
  if (!match) return null;
  return new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
}

function utcDateToDateInput(value) {
  return [
    value.getUTCFullYear(),
    String(value.getUTCMonth() + 1).padStart(2, "0"),
    String(value.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

function addDaysToDateInput(value, days) {
  const dateValue = dateInputToUtcDate(value);
  if (!dateValue) return "";
  dateValue.setUTCDate(dateValue.getUTCDate() + days);
  return utcDateToDateInput(dateValue);
}

function measurementAppointmentLatestDate(deliveryDate) {
  return addDaysToDateInput(deliveryDate, -(MEASUREMENT_APPOINTMENT_BLOCKED_WINDOW_DAYS + 1));
}

function isMeasurementAppointmentAllowed(appointmentDate, deliveryDate) {
  const appointment = dateInputToUtcDate(appointmentDate);
  const latest = dateInputToUtcDate(measurementAppointmentLatestDate(deliveryDate));
  if (!appointment || !latest) return false;
  return appointment <= latest;
}

function StatusPill({ value }) {
  const t = useT();
  const normalized = String(value || "").toUpperCase();
  const danger = ["SUSPENDED", "BLOCKED", "DELETED", "REJECTED", "CANCELLED", "FAILED", "NOT_AVAILABLE", "URGENT", "HIGH", "DISPUTED", "UNVERIFIED BY GATEWAY"].includes(normalized);
  const ok = ["ACTIVE", "APPROVED", "VERIFIED", "COMPLETED", "PAID", "RESOLVED", "CLOSED", "AVAILABLE", "ACCEPTED", "LOW", "GATEWAY VERIFIED"].includes(normalized);
  const fallback = String(value || "-").replaceAll("_", " ");
  return <span className={`pill ${danger ? "danger" : ok ? "ok" : "warn"}`}>{t(`status.${normalized}`, fallback)}</span>;
}

function Empty({ text = "No records yet." }) {
  return <div className="empty">{text}</div>;
}

const DEFAULT_TABLE_PAGE_SIZE = 8;
const DEFAULT_CARD_PAGE_SIZE = 6;

function usePagedRows(rows = [], pageSize = DEFAULT_TABLE_PAGE_SIZE) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const safePageSize = Math.max(1, Number(pageSize) || DEFAULT_TABLE_PAGE_SIZE);
  const [page, setPage] = useState(1);
  const total = safeRows.length;
  const totalPages = Math.max(1, Math.ceil(total / safePageSize));

  useEffect(() => {
    setPage(1);
  }, [total, safePageSize]);

  useEffect(() => {
    setPage((current) => Math.min(Math.max(1, current), totalPages));
  }, [totalPages]);

  const currentPage = Math.min(Math.max(1, page), totalPages);
  const startIndex = total ? (currentPage - 1) * safePageSize : 0;
  const endIndex = total ? Math.min(startIndex + safePageSize, total) : 0;

  return {
    page: currentPage,
    pageSize: safePageSize,
    total,
    totalPages,
    start: total ? startIndex + 1 : 0,
    end: endIndex,
    rows: safeRows.slice(startIndex, endIndex),
    setPage,
  };
}

function PaginationControls({ page, totalPages, total, start, end, onPage, label = "records" }) {
  if (!total || totalPages <= 1) return null;
  const firstPage = Math.max(1, Math.min(page - 2, totalPages - 4));
  const lastPage = Math.min(totalPages, firstPage + 4);
  const pages = [];
  for (let value = firstPage; value <= lastPage; value += 1) pages.push(value);

  return (
    <nav className="pagination-bar" aria-label={`${label} pagination`}>
      <span className="pagination-summary">Showing {start}-{end} of {total} {label}</span>
      <div className="pagination-pages">
        <button type="button" onClick={() => onPage(page - 1)} disabled={page <= 1}>Previous</button>
        {pages.map((value) => (
          <button
            type="button"
            key={value}
            className={value === page ? "active" : ""}
            onClick={() => onPage(value)}
            aria-current={value === page ? "page" : undefined}
          >
            {value}
          </button>
        ))}
        <button type="button" onClick={() => onPage(page + 1)} disabled={page >= totalPages}>Next</button>
      </div>
    </nav>
  );
}

function PaginatedCards({ items = [], pageSize = DEFAULT_CARD_PAGE_SIZE, className = "cards", label = "items", emptyText = "No records yet.", renderItem }) {
  const pageData = usePagedRows(items, pageSize);
  if (!pageData.total) return <Empty text={emptyText} />;
  return (
    <>
      <div className={className}>
        {pageData.rows.map((item, index) => (
          <React.Fragment key={item?.id || item?.code || item?.customerProfileId || item?.customer_profile_id || index}>
            {renderItem(item, index)}
          </React.Fragment>
        ))}
      </div>
      <PaginationControls
        page={pageData.page}
        totalPages={pageData.totalPages}
        total={pageData.total}
        start={pageData.start}
        end={pageData.end}
        onPage={pageData.setPage}
        label={label}
      />
    </>
  );
}

function ViewMoreGrid({ items = [], initial = 6, step = 6, className = "updates-list", label = "items", emptyText = "No records yet.", renderItem }) {
  const safeItems = Array.isArray(items) ? items : [];
  const [visibleCount, setVisibleCount] = useState(initial);

  useEffect(() => {
    setVisibleCount(initial);
  }, [safeItems.length, initial]);

  if (!safeItems.length) return <Empty text={emptyText} />;
  const visibleItems = safeItems.slice(0, visibleCount);
  const canViewMore = visibleCount < safeItems.length;

  return (
    <>
      <div className={className}>
        {visibleItems.map((item, index) => (
          <React.Fragment key={item?.id || item?.code || index}>
            {renderItem(item, index)}
          </React.Fragment>
        ))}
      </div>
      {safeItems.length > initial ? (
        <div className="view-more-row">
          <span>Showing {visibleItems.length} of {safeItems.length} {label}</span>
          {canViewMore ? (
            <button type="button" className="view-more-btn" onClick={() => setVisibleCount((count) => Math.min(count + step, safeItems.length))}>View more</button>
          ) : (
            <button type="button" className="view-more-btn" onClick={() => setVisibleCount(initial)}>Show less</button>
          )}
        </div>
      ) : null}
    </>
  );
}

function portfolioItems(portfolio = []) {
  return portfolio.map((entry, index) => {
    let item = {};
    if (typeof entry === "string") {
      try {
        item = JSON.parse(entry);
      } catch {
        item = { url: entry, name: `Portfolio ${index + 1}` };
      }
    } else {
      item = entry || {};
    }
    const url = assetUrl(item.url || item.dataUrl || item.src || "");
    const type = item.type || "";
    const lowerUrl = url.toLowerCase();
    const isVideo = type.startsWith("video/") || /\.(mp4|webm|mov)(\?|$)/.test(lowerUrl);
    return {
      index,
      id: item.id || `portfolio-${index}`,
      name: item.name || `Portfolio ${index + 1}`,
      type,
      kind: item.kind || (isVideo ? "video" : "image"),
      url,
    };
  }).filter((item) => item.url);
}

function mediaKindFrom(mediaType = "", url = "") {
  const lowerUrl = String(url || "").toLowerCase();
  if (mediaType.startsWith("video/") || /\.(mp4|webm|mov)(\?|$)/.test(lowerUrl)) return "video";
  return "image";
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Could not read selected file"));
    reader.readAsDataURL(file);
  });
}

function TailorAvatar({ tailor, size = "md" }) {
  const image = assetUrl(tailor?.profileImage);
  const initials = String(tailor?.shop || tailor?.ownerName || "TH").trim().slice(0, 2).toUpperCase();
  return (
    <div className={`tailor-avatar ${size}`}>
      {image ? <img src={image} alt={`${tailor.shop} profile`} /> : <span>{initials}</span>}
    </div>
  );
}

function CustomerAvatar({ customer, size = "md" }) {
  const image = assetUrl(customer?.profileImage);
  const source = customer?.name || customer?.fullName || customer?.customerProfileId || "CU";
  const initials = String(source).trim().split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "CU";
  return (
    <div className={`tailor-avatar ${size}`}>
      {image ? <img src={image} alt="Customer profile" /> : <span>{initials}</span>}
    </div>
  );
}

function MediaGallery({ portfolio, onRemove }) {
  const items = portfolioItems(portfolio);
  return (
    <ViewMoreGrid
      items={items}
      initial={6}
      step={6}
      className="media-grid"
      label="media items"
      emptyText="No photos or videos uploaded yet."
      renderItem={(item) => (
        <div className="media-tile">
          {item.kind === "video" ? (
            <video src={item.url} controls preload="metadata" />
          ) : (
            <img src={item.url} alt={item.name} />
          )}
          <div className="media-meta">
            <span>{item.kind === "video" ? <Video size={13} /> : <ImageIcon size={13} />} {item.name}</span>
            {onRemove ? <button type="button" onClick={() => onRemove(item.index)} title="Remove media"><Trash2 size={14} /></button> : null}
          </div>
        </div>
      )}
    />
  );
}

function App() {
  const [referralEntry, setReferralEntry] = useState(() => readReferralEntry());
  const [role, setRole] = useState(() => (!referralEntry && hasValidStoredSession() ? getRole() : ""));
  const [signedIn, setSignedIn] = useState(() => !referralEntry && Boolean(getToken() && getRole()));
  const [theme, setTheme] = useState(initialTheme);
  const [language, setLanguage] = useState(initialLanguage);
  const languageValue = useMemo(() => ({
    language,
    setLanguage,
    t: (key, fallback, values) => translate(language, key, fallback, values),
  }), [language]);

  useEffect(() => {
    function handleSessionCleared() {
      setSignedIn(false);
      setRole("");
    }
    window.addEventListener("tailorahub:session-cleared", handleSessionCleared);
    return () => window.removeEventListener("tailorahub:session-cleared", handleSessionCleared);
  }, []);

  useEffect(() => {
    if (!referralEntry) return;
    clearSession();
    setSignedIn(false);
    setRole("");
  }, [referralEntry]);

  useEffect(() => {
    if (!signedIn) return undefined;

    function expireIfIdle() {
      if (!isSessionExpired()) return false;
      clearSession();
      setSignedIn(false);
      setRole("");
      return true;
    }

    function handleActivity() {
      if (!expireIfIdle()) markSessionActive();
    }

    function handleResume() {
      if (document.visibilityState === "hidden") return;
      handleActivity();
    }

    markSessionActive();
    const activityEvents = ["click", "keydown", "pointerdown", "touchstart", "scroll"];
    activityEvents.forEach((eventName) => window.addEventListener(eventName, handleActivity, { passive: true, capture: true }));
    window.addEventListener("focus", handleResume);
    document.addEventListener("visibilitychange", handleResume);
    const timer = window.setInterval(expireIfIdle, 15000);

    return () => {
      activityEvents.forEach((eventName) => window.removeEventListener(eventName, handleActivity, { capture: true }));
      window.removeEventListener("focus", handleResume);
      document.removeEventListener("visibilitychange", handleResume);
      window.clearInterval(timer);
    };
  }, [signedIn]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("tailorahub-theme", theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = language;
    window.localStorage.setItem("tailorahub-language", language);
  }, [language]);

  function handleAuth(res, selectedRole) {
    const nextRole = res.role || selectedRole;
    setSession(res.token || res.access_token, nextRole, res.refreshToken || res.refresh_token);
    setRole(nextRole);
    setSignedIn(true);
    if (referralEntry) {
      clearReferralBrowserUrl();
      setReferralEntry(null);
    }
  }

  function logout() {
    clearSession();
    setSignedIn(false);
    setRole("");
  }

  let content;
  if (!signedIn) content = <AuthShell onAuth={handleAuth} theme={theme} setTheme={setTheme} language={language} setLanguage={setLanguage} referralEntry={referralEntry} />;
  else if (role === "customer") content = <CustomerApp onLogout={logout} />;
  else if (role === "tailor") content = <TailorApp onLogout={logout} />;
  else content = <AdminApp onLogout={logout} />;

  return <LanguageContext.Provider value={languageValue}>{content}</LanguageContext.Provider>;
}

const tailorWizardSteps = [
  "Aadhaar",
  "Mobile",
  "Email",
  "Experience",
  "Password",
  "Terms",
  "Location",
];

const verhoeffD = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
  [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
  [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
  [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
  [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
  [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
  [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
  [8, 7, 6, 5, 9, 3, 2, 1, 0],
  [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
];
const verhoeffP = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
  [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
  [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
  [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
  [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
  [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
  [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
];

function cleanDigits(value) {
  return String(value || "").replace(/\D/g, "");
}

function isValidIndianPhone(value) {
  return /^[6-9]\d{9}$/.test(cleanDigits(value));
}

function isValidAadhaar(value) {
  const digits = cleanDigits(value);
  if (digits.length !== 12) return false;
  let checksum = 0;
  [...digits].reverse().forEach((digit, index) => {
    checksum = verhoeffD[checksum][verhoeffP[index % 8][Number(digit)]];
  });
  return checksum === 0;
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
}

function passwordScore(value) {
  const password = String(value || "");
  return [
    password.length >= 8,
    /[A-Za-z]/.test(password),
    /\d/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ].filter(Boolean).length;
}

function passwordMessage(password, confirmPassword) {
  if (!password) return "Create a password";
  if (password.length < 8) return "Password must be at least 8 characters";
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return "Password must include one letter and one number";
  if (confirmPassword && password !== confirmPassword) return "Password and confirm password must match";
  return "";
}

function Field({ label, error, success, hint, children, className = "" }) {
  return (
    <label className={`field ${error ? "has-error" : ""} ${className}`}>
      <span>{label}</span>
      {children}
      {error ? <em className="field-error">{error}</em> : success ? <em className="field-success">{success}</em> : hint ? <small>{hint}</small> : null}
    </label>
  );
}

function ThemeToggle({ theme, setTheme }) {
  const nextTheme = theme === "dark" ? "light" : "dark";
  return (
    <button type="button" className={`theme-toggle ${theme}`} onClick={() => setTheme(nextTheme)} aria-label={`Switch to ${nextTheme} theme`}>
      <Moon size={17} />
      <span className="toggle-track"><span /></span>
      <Sun size={17} />
    </button>
  );
}

function LanguageSelect({ language, setLanguage }) {
  const { language: contextLanguage, setLanguage: contextSetLanguage, t } = useLanguage();
  const selectedLanguage = language || contextLanguage;
  const updateLanguage = setLanguage || contextSetLanguage;
  return (
    <label className="language-select" title={t("common.language", "Language")}>
      <Globe2 size={15} />
      <select value={selectedLanguage} onChange={(event) => updateLanguage(event.target.value)} aria-label={t("common.language", "Select language")}>
        {languageOptions.map(([value, label, short]) => (
          <option value={value} key={value}>{short} - {label}</option>
        ))}
      </select>
    </label>
  );
}

function LuxuryRoleCard({ role, active, onSelect }) {
  const t = useT();
  const [id, label, Icon, text] = role;
  const roleLabel = t(`role.${id}.label`, label);
  const roleText = t(`role.${id}.description`, text);
  return (
    <button type="button" className={active ? "role-card luxury-role-card active" : "role-card luxury-role-card"} onClick={() => onSelect(id)}>
      <span className="role-card-icon"><Icon size={22} /></span>
      <strong>{roleLabel}</strong>
      <span className="role-divider" aria-hidden="true" />
      <span>{roleText}</span>
      <span className="role-arrow" aria-hidden="true"><ArrowRight size={24} /></span>
    </button>
  );
}

function AuthShell({ onAuth, theme, setTheme, language, setLanguage, referralEntry }) {
  const t = useT();
  const [authStage, setAuthStage] = useAppHistoryState("authStage", "home");
  const [selectedRole, setSelectedRole] = useState("customer");
  const [mode, setMode] = useState("login");
  const [tailorLoginMode, setTailorLoginMode] = useState("password");
  const [wizardStep, setWizardStep] = useState(0);
  const [form, setForm] = useState({
    identifier: "",
    password: "",
    confirmPassword: "",
    name: "",
    email: "",
    phone: "",
    gender: "",
    zoneId: "tnagar",
    address: "",
    shop: "",
    specs: "Blouse, Alteration",
    serviceName: "Blouse Stitching",
    servicePrice: "650",
    serviceDays: "5",
    years: "0",
    bio: "",
    otp: "",
    username: "",
    aadhaarNumber: "",
    dob: "",
    stitchingSinceDate: "",
    referralCode: "",
    termsAccepted: false,
    location: null,
  });
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [aadhaarVerified, setAadhaarVerified] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [fieldSuccess, setFieldSuccess] = useState({});
  const [checking, setChecking] = useState({});
  const [loginOtp, setLoginOtp] = useState({ sent: false, code: "", target: "", cooldown: 0 });
  const [forgotFlow, setForgotFlow] = useState({
    active: false,
    step: "request",
    identifier: "",
    otp: "",
    newPassword: "",
    confirmPassword: "",
    target: "",
    cooldown: 0,
  });
  const [otpState, setOtpState] = useState({
    phoneSent: false,
    phoneCode: "",
    phoneVerified: false,
    phoneCooldown: 0,
    emailSent: false,
    emailCode: "",
    emailVerified: false,
    emailCooldown: 0,
  });

  useEffect(() => {
    if (!referralEntry?.code) return;
    const referralRole = referralEntry.role === "tailor" ? "tailor" : "customer";
    setSelectedRole(referralRole);
    setMode("register");
    setAuthStage("auth", { replace: true });
    setWizardStep(0);
    setError("");
    setInfo(`${referralRole === "tailor" ? "Tailor" : "Customer"} referral code applied. Register with your own new account details.`);
    setForm((old) => ({
      ...old,
      identifier: "",
      password: "",
      confirmPassword: "",
      referralCode: referralEntry.code,
    }));
  }, [referralEntry?.role, referralEntry?.code, setAuthStage]);

  useEffect(() => {
    if (selectedRole === "admin") setMode("login");
    setWizardStep(0);
    setTailorLoginMode("password");
    setLoginOtp({ sent: false, code: "", target: "", cooldown: 0 });
    setForgotFlow({ active: false, step: "request", identifier: "", otp: "", newPassword: "", confirmPassword: "", target: "", cooldown: 0 });
    setAadhaarVerified(false);
    setFieldErrors({});
    setFieldSuccess({});
    setChecking({});
    setOtpState({
      phoneSent: false,
      phoneCode: "",
      phoneVerified: false,
      phoneCooldown: 0,
      emailSent: false,
      emailCode: "",
      emailVerified: false,
      emailCooldown: 0,
    });
    setForm((old) => ({
      ...old,
      identifier: selectedRole === "admin" ? "admin" : old.email || old.phone,
      password: selectedRole === "admin" ? "" : old.password,
    }));
  }, [selectedRole]);

  useEffect(() => {
    if (!otpState.phoneCooldown && !otpState.emailCooldown) return undefined;
    const timer = setInterval(() => {
      setOtpState((old) => ({
        ...old,
        phoneCooldown: Math.max(0, old.phoneCooldown - 1),
        emailCooldown: Math.max(0, old.emailCooldown - 1),
      }));
    }, 1000);
    return () => clearInterval(timer);
  }, [otpState.phoneCooldown, otpState.emailCooldown]);

  useEffect(() => {
    if (!loginOtp.cooldown && !forgotFlow.cooldown) return undefined;
    const timer = setInterval(() => {
      setLoginOtp((old) => ({ ...old, cooldown: Math.max(0, old.cooldown - 1) }));
      setForgotFlow((old) => ({ ...old, cooldown: Math.max(0, old.cooldown - 1) }));
    }, 1000);
    return () => clearInterval(timer);
  }, [loginOtp.cooldown, forgotFlow.cooldown]);

  useEffect(() => {
    if (mode !== "register" || selectedRole !== "tailor" || !form.phone || !isValidIndianPhone(form.phone)) return undefined;
    const timer = setTimeout(() => checkAvailability("phone", form.phone), 550);
    return () => clearTimeout(timer);
  }, [form.phone, mode, selectedRole]);

  useEffect(() => {
    if (mode !== "register" || selectedRole !== "customer" || !form.phone || !isValidIndianPhone(form.phone)) return undefined;
    const timer = setTimeout(() => checkAvailability("phone", form.phone), 550);
    return () => clearTimeout(timer);
  }, [form.phone, mode, selectedRole]);

  useEffect(() => {
    if (mode !== "register" || selectedRole !== "tailor" || !form.email || !isValidEmail(form.email)) return undefined;
    const timer = setTimeout(() => checkAvailability("email", form.email), 550);
    return () => clearTimeout(timer);
  }, [form.email, mode, selectedRole]);

  useEffect(() => {
    if (mode !== "register" || selectedRole !== "customer" || !form.email || !isValidEmail(form.email)) return undefined;
    const timer = setTimeout(() => checkAvailability("email", form.email), 550);
    return () => clearTimeout(timer);
  }, [form.email, mode, selectedRole]);

  useEffect(() => {
    if (mode !== "register" || selectedRole !== "tailor" || form.username.trim().length < 4) return undefined;
    const timer = setTimeout(() => checkAvailability("username", form.username), 550);
    return () => clearTimeout(timer);
  }, [form.username, mode, selectedRole]);

  useEffect(() => {
    if (mode !== "register" || selectedRole !== "tailor" || !isValidAadhaar(form.aadhaarNumber)) return undefined;
    const timer = setTimeout(() => checkAvailability("aadhaar", form.aadhaarNumber), 550);
    return () => clearTimeout(timer);
  }, [form.aadhaarNumber, mode, selectedRole]);

  function syncError(key, value, nextForm = form) {
    if (key === "phone") return isValidIndianPhone(value) ? "" : "Enter a valid 10-digit Indian mobile number";
    if (key === "email") return selectedRole === "customer" && !value ? "" : isValidEmail(value) ? "" : "Enter a valid email address";
    if (key === "aadhaarNumber") return isValidAadhaar(value) ? "" : "Enter a valid Aadhaar number";
    if (key === "name") return value.trim().length >= 2 ? "" : selectedRole === "customer" ? "Enter your full name" : "Enter the name exactly as on Aadhaar";
    if (key === "dob") return value ? "" : "DOB is required";
    if (key === "username") return value.trim().length >= 4 ? "" : "Username must be at least 4 characters";
    if (key === "years") return value !== "" && Number(value) >= 0 ? "" : "Experience level is required";
    if (key === "stitchingSinceDate") return value ? "" : "Stitching since date is required";
    if (key === "password") return passwordMessage(value, nextForm.confirmPassword);
    if (key === "confirmPassword") return passwordMessage(nextForm.password, value);
    if (key === "termsAccepted") return value ? "" : "Accept the terms and conditions to continue";
    return "";
  }

  function update(key, value) {
    const normalized = key === "phone" || key === "aadhaarNumber" ? cleanDigits(value) : value;
    setForm((old) => {
      const next = { ...old, [key]: normalized };
      setFieldErrors((prev) => ({ ...prev, [key]: syncError(key, normalized, next) }));
      return next;
    });
    setInfo("");
    if (key === "phone") {
      setOtpState((old) => ({ ...old, phoneVerified: false, phoneSent: false, phoneCode: "" }));
      setFieldSuccess((old) => ({ ...old, phone: "" }));
    }
    if (key === "identifier") {
      setLoginOtp((old) => ({ ...old, sent: false, code: "", target: "" }));
    }
    if (key === "email") {
      setOtpState((old) => ({ ...old, emailVerified: false, emailSent: false, emailCode: "" }));
      setFieldSuccess((old) => ({ ...old, email: "" }));
    }
    if (key === "aadhaarNumber" || key === "name" || key === "dob") {
      setAadhaarVerified(false);
      setFieldSuccess((old) => ({ ...old, aadhaarNumber: "" }));
    }
    if (key === "password" || key === "confirmPassword") {
      setFieldErrors((prev) => ({
        ...prev,
        password: key === "password" ? syncError("password", normalized, { ...form, [key]: normalized }) : syncError("password", form.password, { ...form, [key]: normalized }),
        confirmPassword: key === "confirmPassword" ? syncError("confirmPassword", normalized, { ...form, [key]: normalized }) : syncError("confirmPassword", form.confirmPassword, { ...form, [key]: normalized }),
      }));
    }
  }

  async function checkAvailability(field, rawValue) {
    const key = field === "aadhaar" ? "aadhaarNumber" : field;
    const value = field === "phone" || field === "aadhaar" ? cleanDigits(rawValue) : String(rawValue || "").trim();
    if (!value) return false;
    const localError = syncError(key, value);
    if (localError) {
      setFieldErrors((old) => ({ ...old, [key]: localError }));
      return false;
    }
    setChecking((old) => ({ ...old, [key]: true }));
    try {
      const res = selectedRole === "customer"
        ? await api.checkCustomerAvailability(field, value)
        : await api.checkAvailability(field, value);
      setFieldErrors((old) => ({ ...old, [key]: res.available ? "" : res.message }));
      setFieldSuccess((old) => ({ ...old, [key]: res.available ? "Available" : "" }));
      return Boolean(res.available);
    } catch (err) {
      setFieldErrors((old) => ({ ...old, [key]: err.message }));
      return false;
    } finally {
      setChecking((old) => ({ ...old, [key]: false }));
    }
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");
    try {
      if (mode === "login") {
        if (selectedRole === "tailor") {
          await submitTailorLogin();
          return;
        }
        if (selectedRole === "customer") {
          await submitCustomerLogin();
          return;
        }
        const res = await api.login(selectedRole, form.identifier, form.password);
        onAuth(res, selectedRole);
        return;
      }
      if (selectedRole === "tailor") {
        if (!tailorReadyToSubmit) throw new Error(stepError(wizardStep) || "Complete all registration steps first");
        const specs = form.specs.split(",").map((x) => x.trim()).filter(Boolean);
        const payload = {
          full_name: form.name,
          phone_number: cleanDigits(form.phone),
          email: form.email,
          dob: form.dob,
          aadhaar_number: cleanDigits(form.aadhaarNumber),
          gender: form.gender || undefined,
          username: form.username,
          password: form.password,
          confirm_password: form.confirmPassword,
          experience_years_base: Number(form.years || 0),
          stitching_since_date: form.stitchingSinceDate,
          terms_accepted: form.termsAccepted,
          referral_code: form.referralCode || undefined,
          shop_name: form.shop || undefined,
          zone_id: form.zoneId,
          address_text: form.location?.address_text || form.address || undefined,
          latitude: form.location?.latitude,
          longitude: form.location?.longitude,
          bio: form.bio,
          expertise: specs,
          services: [{
            name: form.serviceName,
            garment_id: form.serviceName.toLowerCase().replaceAll(" ", "-"),
            price: Number(form.servicePrice || 0),
            days: Number(form.serviceDays || 5),
            description: `${form.serviceName} made to measure`,
          }],
        };
        const res = await api.registerTailor(payload);
        onAuth(res, selectedRole);
        return;
      }
      const customerError = customerRegistrationError();
      if (customerError) throw new Error(customerError);
      const res = await api.registerCustomer({
        full_name: form.name,
        phone_number: cleanDigits(form.phone),
        email: form.email || undefined,
        password: form.password,
        confirm_password: form.confirmPassword,
        referral_code: form.referralCode || undefined,
        terms_accepted: form.termsAccepted,
      });
      onAuth(res, selectedRole);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitTailorLogin() {
    if (!form.identifier.trim()) throw new Error("Enter your username or mobile number");
    if (tailorLoginMode === "password") {
      if (!form.password) throw new Error("Enter your password");
      const res = await api.tailorV1Login({ identifier: form.identifier, mode: "password", password: form.password });
      onAuth(res, "tailor");
      return;
    }
    if (!loginOtp.sent) {
      const res = await api.tailorV1Login({ identifier: form.identifier, mode: "otp" });
      setLoginOtp({ sent: true, code: "", target: res.target || "", cooldown: 30 });
      setInfo(res.devOtp ? `Dev mode code: ${res.devOtp}` : `OTP sent to ${res.target || "registered contact"}.`);
      return;
    }
    if (!loginOtp.code) throw new Error("Enter the OTP sent to your registered contact");
    const res = await api.tailorV1Login({ identifier: form.identifier, mode: "otp", otp: loginOtp.code });
    onAuth(res, "tailor");
  }

  async function submitCustomerLogin() {
    if (!form.identifier.trim()) throw new Error("Enter your mobile number or email");
    if (tailorLoginMode === "password") {
      if (!form.password) throw new Error("Enter your password");
      const res = await api.customerV1Login({ identifier: form.identifier, mode: "password", password: form.password });
      onAuth(res, "customer");
      return;
    }
    if (!loginOtp.sent) {
      const res = await api.customerV1Login({ identifier: form.identifier, mode: "otp" });
      setLoginOtp({ sent: true, code: "", target: res.target || "", cooldown: 30 });
      setInfo(res.devOtp ? `Dev mode code: ${res.devOtp}` : `OTP sent to ${res.target || "registered contact"}.`);
      return;
    }
    if (!loginOtp.code) throw new Error("Enter the OTP sent to your registered contact");
    const res = await api.customerV1Login({ identifier: form.identifier, mode: "otp", otp: loginOtp.code });
    onAuth(res, "customer");
  }

  async function resendTailorLoginOtp() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      if (!form.identifier.trim()) throw new Error("Enter your username or mobile number");
      const res = await api.tailorV1Login({ identifier: form.identifier, mode: "otp" });
      setLoginOtp({ sent: true, code: "", target: res.target || "", cooldown: 30 });
      setInfo(res.devOtp ? `Dev mode code: ${res.devOtp}` : `OTP sent to ${res.target || "registered contact"}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function resendCustomerLoginOtp() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      if (!form.identifier.trim()) throw new Error("Enter your mobile number or email");
      const res = await api.customerV1Login({ identifier: form.identifier, mode: "otp" });
      setLoginOtp({ sent: true, code: "", target: res.target || "", cooldown: 30 });
      setInfo(res.devOtp ? `Dev mode code: ${res.devOtp}` : `OTP sent to ${res.target || "registered contact"}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendOtp() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const res = await api.requestOtp(form.identifier);
      if (res.delivery?.via === "smtp") {
        setInfo("OTP sent to email. Enter it below and click Verify OTP.");
      } else {
        setInfo(`SMTP is not configured, so OTP was saved to ${res.delivery?.file || "email outbox"}.`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const res = await api.verifyOtp(form.identifier, form.otp);
      if (!res.user || !(res.user.roles || []).includes(selectedRole)) {
        throw new Error(`This email is not registered as ${selectedRole}`);
      }
      onAuth({ ...res, role: selectedRole }, selectedRole);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function openForgotPassword() {
    setError("");
    setInfo("");
    setForgotFlow({
      active: true,
      step: "request",
      identifier: form.identifier,
      otp: "",
      newPassword: "",
      confirmPassword: "",
      target: "",
      cooldown: 0,
    });
  }

  function closeForgotPassword() {
    setError("");
    setInfo("");
    setForgotFlow({ active: false, step: "request", identifier: "", otp: "", newPassword: "", confirmPassword: "", target: "", cooldown: 0 });
  }

  async function sendForgotPasswordOtp() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      if (!forgotFlow.identifier.trim()) throw new Error(selectedRole === "customer" ? "Enter your mobile number or email" : "Enter your username, mobile number or email");
      const res = selectedRole === "customer"
        ? await api.customerForgotPassword(forgotFlow.identifier)
        : await api.tailorForgotPassword(forgotFlow.identifier);
      setForgotFlow((old) => ({ ...old, step: "reset", target: res.target || "", cooldown: 30 }));
      setInfo(res.devOtp ? `Dev mode code: ${res.devOtp}` : `Reset OTP sent to ${res.target || "registered contact"}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function resetForgotPassword() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const message = passwordMessage(forgotFlow.newPassword, forgotFlow.confirmPassword);
      if (!forgotFlow.otp) throw new Error("Enter the OTP");
      if (message) throw new Error(message);
      const payload = {
        identifier: forgotFlow.identifier,
        otp: forgotFlow.otp,
        new_password: forgotFlow.newPassword,
        confirm_password: forgotFlow.confirmPassword,
      };
      if (selectedRole === "customer") await api.customerResetPassword(payload);
      else await api.tailorResetPassword(payload);
      update("identifier", forgotFlow.identifier);
      update("password", "");
      setTailorLoginMode("password");
      closeForgotPassword();
      setInfo("Password updated. You can now sign in.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // Registration-time phone/email verification (file 05) -- separate purpose-scoped
  // OTP pool from the login flow above, required by the backend before a tailor
  // account can be created.
  async function sendRegistrationOtp(kind) {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const target = kind === "phone" ? form.phone : form.email;
      if (!target) throw new Error(kind === "phone" ? "Enter your mobile number first" : "Enter your email first");
      const available = await checkAvailability(kind, target);
      if (!available) {
        const res = selectedRole === "customer"
          ? await api.checkCustomerAvailability(kind, target)
          : await api.checkAvailability(kind, target);
        throw new Error(res.message || (kind === "phone" ? "Fix mobile number first" : "Fix email first"));
      }
      const purpose = kind === "phone" ? "registration_phone" : "registration_email";
      const res = await api.sendPurposeOtp(target, purpose);
      const devOtp = res.dev_otp || res.devOtp;
      setOtpState((old) => ({
        ...old,
        [`${kind}Sent`]: true,
        [`${kind}Cooldown`]: 30,
      }));
      setInfo(devOtp ? `Dev mode code: ${devOtp}` : `Code sent to your ${kind === "phone" ? "mobile number" : "email"}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function verifyRegistrationOtp(kind) {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const target = kind === "phone" ? form.phone : form.email;
      const code = kind === "phone" ? otpState.phoneCode : otpState.emailCode;
      const purpose = kind === "phone" ? "registration_phone" : "registration_email";
      await api.verifyPurposeOtp(target, purpose, code);
      setOtpState((old) => ({ ...old, [`${kind}Verified`]: true }));
      setInfo(`${kind === "phone" ? "Mobile number" : "Email"} verified.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function verifyAadhaar() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const checks = {
        name: syncError("name", form.name),
        dob: syncError("dob", form.dob),
        aadhaarNumber: syncError("aadhaarNumber", form.aadhaarNumber),
      };
      setFieldErrors((old) => ({ ...old, ...checks }));
      if (Object.values(checks).some(Boolean)) throw new Error("Complete Aadhaar details first");
      const available = await checkAvailability("aadhaar", form.aadhaarNumber);
      if (!available) {
        const res = await api.checkAvailability("aadhaar", form.aadhaarNumber);
        throw new Error(res.message || "Fix Aadhaar number first");
      }
      const res = await api.verifyTailorAadhaar({
        aadhaar_number: cleanDigits(form.aadhaarNumber),
        full_name: form.name,
        dob: form.dob,
      });
      setForm((old) => ({ ...old, name: res.fullName || old.name, dob: res.dob || old.dob }));
      setAadhaarVerified(true);
      setFieldSuccess((old) => ({ ...old, aadhaarNumber: "Aadhaar verified" }));
      setInfo("Aadhaar verified.");
    } catch (err) {
      setAadhaarVerified(false);
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function customerRegistrationError() {
    if (!form.name.trim()) return "Enter your full name";
    if (!isValidIndianPhone(form.phone)) return "Enter a valid 10-digit mobile number";
    if (fieldErrors.phone) return fieldErrors.phone;
    if (!otpState.phoneVerified) return "Verify your mobile number";
    if (form.email && !isValidEmail(form.email)) return "Enter a valid email address";
    if (fieldErrors.email) return fieldErrors.email;
    if (!form.confirmPassword) return "Confirm your password";
    if (passwordMessage(form.password, form.confirmPassword)) return passwordMessage(form.password, form.confirmPassword);
    if (!form.termsAccepted) return "Accept the terms and conditions";
    return "";
  }

  function stepError(index) {
    if (index === 0) {
      if (!form.name.trim() || !form.dob || !isValidAadhaar(form.aadhaarNumber)) return "Complete and verify Aadhaar details";
      if (fieldErrors.name || fieldErrors.dob || fieldErrors.aadhaarNumber) return fieldErrors.name || fieldErrors.dob || fieldErrors.aadhaarNumber;
      if (!aadhaarVerified) return "Verify Aadhaar before continuing";
    }
    if (index === 1) {
      if (!isValidIndianPhone(form.phone)) return "Enter a valid 10-digit mobile number";
      if (fieldErrors.phone) return fieldErrors.phone;
      if (!otpState.phoneVerified) return "Verify your mobile number";
    }
    if (index === 2) {
      if (!isValidEmail(form.email)) return "Enter a valid email address";
      if (fieldErrors.email) return fieldErrors.email;
      if (!otpState.emailVerified) return "Verify your email";
    }
    if (index === 3) {
      if (!form.shop.trim()) return "Enter shop name";
      if (fieldErrors.years || fieldErrors.stitchingSinceDate) return fieldErrors.years || fieldErrors.stitchingSinceDate;
      if (!form.stitchingSinceDate) return "Choose stitching since date";
      if (Number(form.servicePrice || 0) <= 0) return "Enter service price";
    }
    if (index === 4) {
      const usernameError = syncError("username", form.username);
      if (usernameError) return usernameError;
      if (!form.confirmPassword) return "Confirm your password";
      if (fieldErrors.username || fieldErrors.password || fieldErrors.confirmPassword) return fieldErrors.username || fieldErrors.password || fieldErrors.confirmPassword;
      if (passwordMessage(form.password, form.confirmPassword)) return passwordMessage(form.password, form.confirmPassword);
    }
    if (index === 5 && !form.termsAccepted) return "Accept the terms and conditions";
    if (index === 6 && !form.location) return "Confirm your fixed shop location";
    return "";
  }

  function goNext() {
    const message = stepError(wizardStep);
    if (message) {
      setError(message);
      return;
    }
    setError("");
    setInfo("");
    setWizardStep((step) => Math.min(tailorWizardSteps.length - 1, step + 1));
  }

  function goBack() {
    setError("");
    setInfo("");
    setWizardStep((step) => Math.max(0, step - 1));
  }

  const tailorReadyToSubmit = tailorWizardSteps.every((_, index) => !stepError(index));
  const strength = passwordScore(form.password);
  const referralLockedRole = referralEntry?.code ? (referralEntry.role === "tailor" ? "tailor" : "customer") : "";
  const authRoles = referralLockedRole ? roles.filter(([id]) => id === referralLockedRole) : roles;
  const selectedRoleDetails = roles.find(([id]) => id === selectedRole) || roles[0];
  const selectedRoleLabel = t(`role.${selectedRoleDetails[0]}.label`, selectedRoleDetails[1]);
  const selectedRoleText = t(`role.${selectedRoleDetails[0]}.description`, selectedRoleDetails[3]);

  function chooseRole(roleId) {
    setSelectedRole(roleId);
    setMode("login");
    setAuthStage("auth");
  }

  function backToHome() {
    setAuthStage("home");
    setError("");
    setInfo("");
    setForgotFlow({ active: false, step: "request", identifier: "", otp: "", newPassword: "", confirmPassword: "", target: "", cooldown: 0 });
  }

  function renderTailorLogin() {
    if (forgotFlow.active) return renderForgotPassword();
    return (
      <div className="tailor-login-panel">
        <div className="segmented login-mode-toggle">
          <button
            type="button"
            className={tailorLoginMode === "password" ? "active" : ""}
            onClick={() => {
              setTailorLoginMode("password");
              setLoginOtp({ sent: false, code: "", target: "", cooldown: 0 });
              setError("");
              setInfo("");
            }}
          >
            {t("auth.passwordMode", "Password")}
          </button>
          <button
            type="button"
            className={tailorLoginMode === "otp" ? "active" : ""}
            onClick={() => {
              setTailorLoginMode("otp");
              setLoginOtp({ sent: false, code: "", target: "", cooldown: 0 });
              setError("");
              setInfo("");
            }}
          >
            {t("auth.otpMode", "OTP")}
          </button>
        </div>
        <Field label={t("auth.usernameOrMobile", "Username or mobile number")}>
          <input value={form.identifier} onChange={(e) => update("identifier", e.target.value)} autoComplete="username" placeholder="username or 10 digit mobile" />
        </Field>
        {tailorLoginMode === "password" ? (
          <>
            <Field label={t("common.password", "Password")}>
              <input value={form.password} onChange={(e) => update("password", e.target.value)} type="password" autoComplete="current-password" />
            </Field>
            <button type="button" className="text-link" onClick={openForgotPassword}>{t("auth.forgotPassword", "Forgot password?")}</button>
          </>
        ) : (
          <div className="otp-box">
            {loginOtp.sent ? (
              <>
                <Field label={t("auth.otpCode", "OTP code")} hint={loginOtp.target ? `Sent to ${loginOtp.target}` : "Sent to registered contact"}>
                  <input value={loginOtp.code} onChange={(e) => setLoginOtp((old) => ({ ...old, code: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} placeholder="6 digit OTP" />
                </Field>
                <button type="button" className="text-link" onClick={resendTailorLoginOtp} disabled={busy || loginOtp.cooldown > 0}>
                  {loginOtp.cooldown > 0 ? `Resend in ${loginOtp.cooldown}s` : "Resend OTP"}
                </button>
              </>
            ) : (
              <div className="notice">Use your registered mobile number or username. We will send a login OTP to your registered contact.</div>
            )}
          </div>
        )}
      </div>
    );
  }

  function renderCustomerLogin() {
    if (forgotFlow.active) return renderForgotPassword();
    return (
      <div className="tailor-login-panel">
        <div className="segmented login-mode-toggle">
          <button
            type="button"
            className={tailorLoginMode === "password" ? "active" : ""}
            onClick={() => {
              setTailorLoginMode("password");
              setLoginOtp({ sent: false, code: "", target: "", cooldown: 0 });
              setError("");
              setInfo("");
            }}
          >
            {t("auth.passwordMode", "Password")}
          </button>
          <button
            type="button"
            className={tailorLoginMode === "otp" ? "active" : ""}
            onClick={() => {
              setTailorLoginMode("otp");
              setLoginOtp({ sent: false, code: "", target: "", cooldown: 0 });
              setError("");
              setInfo("");
            }}
          >
            {t("auth.otpMode", "OTP")}
          </button>
        </div>
        <Field label={t("auth.mobileOrEmail", "Mobile number or email")}>
          <input value={form.identifier} onChange={(e) => update("identifier", e.target.value)} autoComplete="username" placeholder="10 digit mobile or email" />
        </Field>
        {tailorLoginMode === "password" ? (
          <>
            <Field label={t("common.password", "Password")}>
              <input value={form.password} onChange={(e) => update("password", e.target.value)} type="password" autoComplete="current-password" />
            </Field>
            <button type="button" className="text-link" onClick={openForgotPassword}>{t("auth.forgotPassword", "Forgot password?")}</button>
          </>
        ) : (
          <div className="otp-box">
            {loginOtp.sent ? (
              <>
                <Field label={t("auth.otpCode", "OTP code")} hint={loginOtp.target ? `Sent to ${loginOtp.target}` : "Sent to registered contact"}>
                  <input value={loginOtp.code} onChange={(e) => setLoginOtp((old) => ({ ...old, code: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} placeholder="6 digit OTP" />
                </Field>
                <button type="button" className="text-link" onClick={resendCustomerLoginOtp} disabled={busy || loginOtp.cooldown > 0}>
                  {loginOtp.cooldown > 0 ? `Resend in ${loginOtp.cooldown}s` : "Resend OTP"}
                </button>
              </>
            ) : (
              <div className="notice">Use your registered mobile number or email. We will send a login OTP to your registered contact.</div>
            )}
          </div>
        )}
      </div>
    );
  }

  function renderForgotPassword() {
    const resetPasswordError = forgotFlow.step === "reset" ? passwordMessage(forgotFlow.newPassword, forgotFlow.confirmPassword) : "";
    const isCustomer = selectedRole === "customer";
    return (
      <div className="forgot-panel">
        <div className="section-head">
          <div>
            <h3>{isCustomer ? t("auth.resetCustomer", "Reset customer password") : t("auth.resetTailor", "Reset tailor password")}</h3>
            <small>{forgotFlow.step === "request" ? (isCustomer ? "Enter your registered mobile number or email." : "Enter your registered username, mobile number or email.") : `OTP sent to ${forgotFlow.target || "registered contact"}.`}</small>
          </div>
          <button type="button" className="text-link" onClick={closeForgotPassword}>{t("auth.backToLogin", "Back to login")}</button>
        </div>
        {forgotFlow.step === "request" ? (
          <>
            <Field label={isCustomer ? t("auth.mobileOrEmail", "Mobile number or email") : t("auth.usernameOrMobile", "Username, mobile number or email")}>
              <input value={forgotFlow.identifier} onChange={(e) => setForgotFlow((old) => ({ ...old, identifier: e.target.value }))} autoComplete="username" />
            </Field>
            <button type="button" className="primary-btn" onClick={sendForgotPasswordOtp} disabled={busy}>{busy ? t("common.pleaseWait", "Please wait...") : t("auth.sendResetOtp", "Send reset OTP")}</button>
          </>
        ) : (
          <>
            <Field label={t("auth.otpCode", "OTP code")}>
              <input value={forgotFlow.otp} onChange={(e) => setForgotFlow((old) => ({ ...old, otp: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} />
            </Field>
            <Field label={t("auth.newPassword", "New password")} error={forgotFlow.newPassword ? resetPasswordError : ""}>
              <input value={forgotFlow.newPassword} onChange={(e) => setForgotFlow((old) => ({ ...old, newPassword: e.target.value }))} type="password" autoComplete="new-password" />
            </Field>
            <Field label={t("auth.confirmNewPassword", "Confirm new password")} error={forgotFlow.confirmPassword && resetPasswordError ? resetPasswordError : ""}>
              <input value={forgotFlow.confirmPassword} onChange={(e) => setForgotFlow((old) => ({ ...old, confirmPassword: e.target.value }))} type="password" autoComplete="new-password" />
            </Field>
            <div className="inline-actions">
              <button type="button" className="secondary-btn" onClick={sendForgotPasswordOtp} disabled={busy || forgotFlow.cooldown > 0}>
                {forgotFlow.cooldown > 0 ? `Resend in ${forgotFlow.cooldown}s` : "Resend OTP"}
              </button>
              <button type="button" className="primary-btn" onClick={resetForgotPassword} disabled={busy}>{busy ? t("common.pleaseWait", "Please wait...") : t("auth.resetPassword", "Reset password")}</button>
            </div>
          </>
        )}
      </div>
    );
  }

  function renderCustomerRegistration() {
    const customerError = customerRegistrationError();
    const customerStrength = passwordScore(form.password);
    return (
      <div className="customer-register-panel">
        <div className="form-grid">
          <Field label={t("auth.fullName", "Full name")} error={fieldErrors.name}>
            <input value={form.name} onChange={(e) => update("name", e.target.value)} autoComplete="name" />
          </Field>
          <Field label={t("auth.emailOptional", "Email (optional)")} error={fieldErrors.email} success={fieldSuccess.email || (checking.email ? "Checking..." : "")}>
            <input value={form.email} onChange={(e) => update("email", e.target.value)} onBlur={() => form.email && checkAvailability("email", form.email)} type="email" autoComplete="email" placeholder="Verify later, not required now" />
          </Field>
          <Field label={t("auth.mobileNumber", "Mobile number")} error={fieldErrors.phone} success={otpState.phoneVerified ? "Mobile number verified" : fieldSuccess.phone || (checking.phone ? "Checking..." : "")}>
            <input value={form.phone} onChange={(e) => update("phone", e.target.value)} onBlur={() => checkAvailability("phone", form.phone)} inputMode="numeric" maxLength={10} autoComplete="tel" />
          </Field>
          <Field label={t("auth.sixDigitOtp", "6 digit OTP")} error={otpState.phoneSent && !otpState.phoneVerified && !otpState.phoneCode ? "Enter the OTP sent to mobile" : ""}>
            <input value={otpState.phoneCode} onChange={(e) => setOtpState((old) => ({ ...old, phoneCode: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} disabled={otpState.phoneVerified} />
          </Field>
          <div className="span-2 inline-actions">
            <button type="button" className="secondary-btn" onClick={() => sendRegistrationOtp("phone")} disabled={busy || otpState.phoneVerified || otpState.phoneCooldown > 0}>{otpState.phoneCooldown > 0 ? `Resend in ${otpState.phoneCooldown}s` : otpState.phoneSent ? "Resend OTP" : "Send OTP"}</button>
            <button type="button" className="ok-btn" onClick={() => verifyRegistrationOtp("phone")} disabled={busy || otpState.phoneVerified || !otpState.phoneSent}>Verify OTP</button>
          </div>
          <Field label={t("common.password", "Password")} error={fieldErrors.password}>
            <input value={form.password} onChange={(e) => update("password", e.target.value)} type="password" autoComplete="new-password" />
          </Field>
          <Field label={t("auth.confirmPassword", "Confirm password")} error={fieldErrors.confirmPassword}>
            <input value={form.confirmPassword} onChange={(e) => update("confirmPassword", e.target.value)} type="password" autoComplete="new-password" />
          </Field>
          <div className="span-2 strength-meter" data-score={customerStrength}>
            <span style={{ width: `${Math.max(customerStrength, 1) * 25}%` }} />
            <small>{customerStrength >= 3 ? t("auth.strongPassword", "Strong password") : t("auth.passwordHint", "Use 8+ chars with letters and numbers")}</small>
          </div>
          <Field label={t("auth.referralOptional", "Referral code (optional)")} className="span-2">
            <input value={form.referralCode} onChange={(e) => update("referralCode", e.target.value.toUpperCase())} placeholder="Optional customer referral code" />
          </Field>
        </div>
        <div className="terms-panel customer-terms">
          <label className="check-row">
            <input type="checkbox" checked={form.termsAccepted} onChange={(e) => update("termsAccepted", e.target.checked)} />
            <span>{t("auth.customerTerms", "I accept TailoraHub Terms & Conditions.")}</span>
          </label>
          {fieldErrors.termsAccepted ? <em className="field-error">{fieldErrors.termsAccepted}</em> : null}
        </div>
        {customerError ? <small className="form-hint">{customerError}</small> : null}
      </div>
    );
  }

  function renderTailorStep() {
    if (wizardStep === 0) {
      return (
        <div className="wizard-grid">
          <Field label="Aadhaar number" error={fieldErrors.aadhaarNumber} success={fieldSuccess.aadhaarNumber || (checking.aadhaarNumber ? "Checking..." : "")}>
            <input value={form.aadhaarNumber} onChange={(e) => update("aadhaarNumber", e.target.value)} onBlur={() => checkAvailability("aadhaar", form.aadhaarNumber)} inputMode="numeric" maxLength={12} placeholder="12 digits" readOnly={aadhaarVerified} />
          </Field>
          <Field label="Full name" error={fieldErrors.name} hint="Must match Aadhaar name">
            <input value={form.name} onChange={(e) => update("name", e.target.value)} readOnly={aadhaarVerified} />
          </Field>
          <Field label="Date of birth" error={fieldErrors.dob}>
            <input value={form.dob} onChange={(e) => update("dob", e.target.value)} type="date" readOnly={aadhaarVerified} />
          </Field>
          <div className="span-2 inline-actions">
            <button type="button" className="secondary-btn" onClick={verifyAadhaar} disabled={busy || aadhaarVerified}>{aadhaarVerified ? "Aadhaar Verified" : "Verify eKYC"}</button>
          </div>
        </div>
      );
    }
    if (wizardStep === 1) {
      return (
        <div className="wizard-grid">
          <Field label="Mobile number" error={fieldErrors.phone} success={otpState.phoneVerified ? "Mobile number verified" : fieldSuccess.phone || (checking.phone ? "Checking..." : "")}>
            <input value={form.phone} onChange={(e) => update("phone", e.target.value)} onBlur={() => checkAvailability("phone", form.phone)} inputMode="numeric" maxLength={10} />
          </Field>
          <Field label="6 digit OTP" error={otpState.phoneSent && !otpState.phoneVerified && !otpState.phoneCode ? "Enter the OTP sent to mobile" : ""}>
            <input value={otpState.phoneCode} onChange={(e) => setOtpState((old) => ({ ...old, phoneCode: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} disabled={otpState.phoneVerified} />
          </Field>
          <div className="span-2 inline-actions">
            <button type="button" className="secondary-btn" onClick={() => sendRegistrationOtp("phone")} disabled={busy || otpState.phoneVerified || otpState.phoneCooldown > 0}>{otpState.phoneCooldown > 0 ? `Resend in ${otpState.phoneCooldown}s` : otpState.phoneSent ? "Resend OTP" : "Send OTP"}</button>
            <button type="button" className="ok-btn" onClick={() => verifyRegistrationOtp("phone")} disabled={busy || otpState.phoneVerified || !otpState.phoneSent}>Verify OTP</button>
          </div>
        </div>
      );
    }
    if (wizardStep === 2) {
      return (
        <div className="wizard-grid">
          <Field label="Email" error={fieldErrors.email} success={otpState.emailVerified ? "Email verified" : fieldSuccess.email || (checking.email ? "Checking..." : "")}>
            <input value={form.email} onChange={(e) => update("email", e.target.value)} onBlur={() => checkAvailability("email", form.email)} type="email" />
          </Field>
          <Field label="6 digit OTP" error={otpState.emailSent && !otpState.emailVerified && !otpState.emailCode ? "Enter the OTP sent to email" : ""}>
            <input value={otpState.emailCode} onChange={(e) => setOtpState((old) => ({ ...old, emailCode: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} disabled={otpState.emailVerified} />
          </Field>
          <div className="span-2 inline-actions">
            <button type="button" className="secondary-btn" onClick={() => sendRegistrationOtp("email")} disabled={busy || otpState.emailVerified || otpState.emailCooldown > 0}>{otpState.emailCooldown > 0 ? `Resend in ${otpState.emailCooldown}s` : otpState.emailSent ? "Resend OTP" : "Send OTP"}</button>
            <button type="button" className="ok-btn" onClick={() => verifyRegistrationOtp("email")} disabled={busy || otpState.emailVerified || !otpState.emailSent}>Verify OTP</button>
          </div>
        </div>
      );
    }
    if (wizardStep === 3) {
      return (
        <div className="wizard-grid">
          <Field label="Shop name"><input value={form.shop} onChange={(e) => update("shop", e.target.value)} /></Field>
          <Field label="Gender">
            <select value={form.gender} onChange={(e) => update("gender", e.target.value)}>
              <option value="">Select gender</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="non_binary">Non-binary</option>
              <option value="prefer_not_to_say">Prefer not to say</option>
            </select>
          </Field>
          <Field label="Experience level" error={fieldErrors.years}><input value={form.years} onChange={(e) => update("years", e.target.value)} type="number" min="0" step="0.5" /></Field>
          <Field label="Stitching since" error={fieldErrors.stitchingSinceDate}><input value={form.stitchingSinceDate} onChange={(e) => update("stitchingSinceDate", e.target.value)} type="date" /></Field>
          <Field label="Expertise"><input value={form.specs} onChange={(e) => update("specs", e.target.value)} placeholder="Blouse, Alteration" /></Field>
          <Field label="Service name"><input value={form.serviceName} onChange={(e) => update("serviceName", e.target.value)} /></Field>
          <Field label="Service price"><input value={form.servicePrice} onChange={(e) => update("servicePrice", e.target.value)} type="number" min="1" /></Field>
          <Field label="Completion days"><input value={form.serviceDays} onChange={(e) => update("serviceDays", e.target.value)} type="number" min="1" /></Field>
          <Field label="About" className="span-2"><textarea value={form.bio} onChange={(e) => update("bio", e.target.value)} /></Field>
        </div>
      );
    }
    if (wizardStep === 4) {
      return (
        <div className="wizard-grid">
          <Field label="Username" error={fieldErrors.username} success={fieldSuccess.username || (checking.username ? "Checking..." : "")}>
            <input value={form.username} onChange={(e) => update("username", e.target.value)} onBlur={() => checkAvailability("username", form.username)} />
          </Field>
          <Field label="Referral code (optional)"><input value={form.referralCode} onChange={(e) => update("referralCode", e.target.value.toUpperCase())} /></Field>
          <Field label="Password" error={fieldErrors.password}>
            <input value={form.password} onChange={(e) => update("password", e.target.value)} type="password" />
          </Field>
          <Field label="Confirm password" error={fieldErrors.confirmPassword}>
            <input value={form.confirmPassword} onChange={(e) => update("confirmPassword", e.target.value)} type="password" />
          </Field>
          <div className="span-2 strength-meter" data-score={strength}>
            <span style={{ width: `${Math.max(strength, 1) * 25}%` }} />
            <small>{strength >= 3 ? "Strong password" : "Use 8+ chars with letters and numbers"}</small>
          </div>
        </div>
      );
    }
    if (wizardStep === 5) {
      return (
        <div className="terms-panel">
          <label className="check-row">
            <input type="checkbox" checked={form.termsAccepted} onChange={(e) => update("termsAccepted", e.target.checked)} />
            <span>I accept TailoraHub Terms &amp; Conditions and confirm that the submitted identity details are correct.</span>
          </label>
          {fieldErrors.termsAccepted ? <em className="field-error">{fieldErrors.termsAccepted}</em> : null}
        </div>
      );
    }
    return (
      <div className="wizard-grid">
        <Field label="Area / zone"><input value={form.zoneId} onChange={(e) => update("zoneId", e.target.value)} /></Field>
        <Field label="Address search text"><input value={form.address} onChange={(e) => update("address", e.target.value)} placeholder="Shop address or nearby landmark" /></Field>
        <div className="span-2">
          <MapPicker
            initialLocation={form.location || { address_text: form.address }}
            onConfirm={(location) => {
              update("location", location);
              update("address", location.address_text);
              setInfo("Fixed shop location confirmed.");
            }}
          />
          {form.location ? <div className="notice ok">Fixed location confirmed and will be saved with registration.</div> : null}
        </div>
      </div>
    );
  }

  if (authStage === "home") {
    return (
      <main className="login-shell luxury-home-shell">
        <section className="luxury-home">
          <header className="home-topbar ppt-home-topbar">
            <div className="ppt-logo">
              <div className="ppt-monogram">
                <Crown size={28} />
                <span>T</span>
              </div>
              <strong>TAILORAHUB</strong>
              <small><span /> PREMIUM FASHION <span /></small>
            </div>
            <div className="home-controls">
              <ThemeToggle theme={theme} setTheme={setTheme} />
              <LanguageSelect language={language} setLanguage={setLanguage} />
            </div>
          </header>

          <div className="ppt-center-brand">
            <h2>TAILORAHUB</h2>
            <div className="ppt-ornament" aria-hidden="true"><span /><b>*</b><span /></div>
            <p>{t("home.tagline", "Where Style Meets Perfection")}</p>
          </div>

          <div className="role-grid luxury-role-grid" aria-label={t("home.chooseRole", "Choose role")}>
            {roles.map((role) => (
              <LuxuryRoleCard key={role[0]} role={role} active={selectedRole === role[0]} onSelect={chooseRole} />
            ))}
          </div>

          <div className="mobile-home-benefits" aria-hidden="true">
            <span><BadgeCheck size={26} />{t("home.verifiedTailors", "Verified Tailors")}</span>
            <span><CreditCard size={26} />{t("home.securePayments", "Secure Payments")}</span>
            <span><Star size={26} />{t("home.premiumExperience", "Premium Experience")}</span>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="login-shell auth-route-shell">
      <section className="auth-panel auth-stage-panel">
        <div className="auth-visual-panel" aria-hidden="true">
          <span className="luxury-eyebrow">{t("auth.atelier", "TailoraHub atelier")}</span>
          <h2>{t("auth.accessTitle", `${selectedRoleLabel} access`, { role: selectedRoleLabel })}</h2>
          <p>{selectedRoleText}</p>
          <div className="visual-metrics">
            <span><b>3</b> {t("common.roles", "roles")}</span>
            <span><b>Live</b> {t("common.orders", "orders")}</span>
            <span><b>OTP</b> secured</span>
          </div>
        </div>
        <div className="auth-form-panel">
          <div className="auth-back-row">
            {referralLockedRole ? (
              <span className="referral-lock-note">{selectedRoleLabel} referral signup</span>
            ) : (
              <button type="button" className="text-link back-link" onClick={backToHome}><ChevronLeft size={16} /> {t("auth.roleSelection", "Role selection")}</button>
            )}
          </div>
          <div className="brand-row">
            <div className="brand-mark">TH</div>
            <div>
              <h1>TailoraHub</h1>
              <p>{mode === "login" ? t("auth.loginSubtitle", `${selectedRoleLabel} login`, { role: selectedRoleLabel }) : t("auth.registrationSubtitle", `${selectedRoleLabel} registration`, { role: selectedRoleLabel })}</p>
            </div>
          </div>
          <div className="role-grid compact-role-grid">
            {authRoles.map((role) => (
              <LuxuryRoleCard key={role[0]} role={role} active={selectedRole === role[0]} onSelect={(roleId) => {
                if (referralLockedRole) return;
                setSelectedRole(roleId);
                setMode("login");
              }} />
            ))}
          </div>
          <div className="segmented">
            {!referralLockedRole ? <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>{t("common.login", "Login")}</button> : null}
            {selectedRole !== "admin" ? <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>{t("common.register", "Register")}</button> : null}
          </div>
          <form onSubmit={submit}>
          {mode === "login" && selectedRole === "tailor" ? (
            renderTailorLogin()
          ) : mode === "login" && selectedRole === "customer" ? (
            renderCustomerLogin()
          ) : mode === "login" ? (
            <>
              <Field label={selectedRole === "admin" ? t("auth.adminIdentifier", "Admin username or email") : t("auth.mobileOrEmail", "Email or mobile number")}>
                <input value={form.identifier} onChange={(e) => update("identifier", e.target.value)} autoComplete="username" />
              </Field>
              <Field label={t("common.password", "Password")}>
                <input value={form.password} onChange={(e) => update("password", e.target.value)} type="password" autoComplete="current-password" />
              </Field>
              {selectedRole !== "admin" ? (
                <div className="otp-box">
                  <Field label={t("auth.emailOtp", "Email OTP")}>
                    <input value={form.otp} onChange={(e) => update("otp", e.target.value)} placeholder="6 digit OTP" />
                  </Field>
                  <div className="inline-actions">
                    <button type="button" onClick={sendOtp} disabled={busy}>{t("auth.sendOtp", "Send OTP")}</button>
                    <button type="button" onClick={verifyOtp} disabled={busy}>{t("auth.verifyOtp", "Verify OTP")}</button>
                  </div>
                </div>
              ) : null}
            </>
          ) : selectedRole === "tailor" ? (
            <div className="tailor-wizard">
              <ol className="stepper">
                {tailorWizardSteps.map((label, index) => (
                  <li key={label} className={index === wizardStep ? "active" : index < wizardStep ? "done" : ""}>
                    <span>{index + 1}</span>
                    <b>{t(`wizard.${label}`, label)}</b>
                  </li>
                ))}
              </ol>
              <div className="wizard-card">{renderTailorStep()}</div>
              <div className="wizard-actions">
                {wizardStep > 0 ? <button type="button" className="secondary-btn" onClick={goBack}>{t("common.back", "Back")}</button> : <span />}
                {wizardStep < tailorWizardSteps.length - 1 ? (
                  <button type="button" className="primary-btn" onClick={goNext} disabled={busy}>{t("common.continue", "Continue")}</button>
                ) : (
                  <button className="primary-btn" disabled={busy || !tailorReadyToSubmit}>{busy ? t("common.pleaseWait", "Please wait...") : t("auth.createTailor", "Create tailor account")}</button>
                )}
              </div>
            </div>
          ) : (
            renderCustomerRegistration()
          )}
          {info ? <div className="notice ok">{info}</div> : null}
          {error ? <div className="error">{error}</div> : null}
          {(mode === "login" && !forgotFlow.active) || (mode === "register" && selectedRole !== "tailor") ? (
            <button className="primary-btn" disabled={busy || (mode === "register" && selectedRole === "customer" && Boolean(customerRegistrationError()))}>
              {busy ? t("common.pleaseWait", "Please wait...") : mode === "login" && ["tailor", "customer"].includes(selectedRole) && tailorLoginMode === "otp" ? (loginOtp.sent ? t("auth.verifyOtpLogin", "Verify OTP and login") : t("auth.sendLoginOtp", "Send login OTP")) : mode === "login" ? t("auth.loginAs", `Login as ${selectedRole}`, { role: selectedRoleLabel }) : t("auth.createAccount", `Create ${selectedRole} account`, { role: selectedRoleLabel })}
            </button>
          ) : null}
          </form>
        </div>
      </section>
    </main>
  );
}

function Shell({ title, subtitle, icon: Icon, onLogout, children, actions }) {
  const { language, setLanguage, t } = useLanguage();
  return (
    <div className="page-shell">
      <header className="app-header">
        <div className="brand-row compact no-border">
          <div className="brand-mark">TH</div>
          <div>
            <div className="eyebrow"><Icon size={14} /> {subtitle}</div>
            <h2>{title}</h2>
          </div>
        </div>
        <div className="top-actions">
          <LanguageSelect language={language} setLanguage={setLanguage} />
          {actions}
          <button className="icon-btn" onClick={onLogout} title={t("common.logout", "Logout")}><LogOut size={17} /></button>
        </div>
      </header>
      {children}
    </div>
  );
}

function customerTailorSearchText(tailor) {
  return [
    tailor.shop,
    tailor.ownerName,
    tailor.zoneId,
    tailor.shopAddress,
    tailor.rating ? `${Number(tailor.rating).toFixed(1)} rating` : "",
    tailor.rating ? `${Number(tailor.rating).toFixed(1)} star` : "",
    tailor.distanceKm ? `${tailor.distanceKm} km` : "",
    tailor.experienceDisplay ? `${tailor.experienceDisplay} years` : "",
    ...(tailor.expertise || []),
  ].join(" ").toLowerCase();
}

function filterCustomerTailors(rows, filters) {
  const tokens = String(filters.q || "").trim().toLowerCase().split(/\s+/).filter(Boolean);
  return rows.filter((tailor) => {
    if (filters.availability && tailor.availability !== filters.availability) return false;
    if (filters.ratingMin && Number(tailor.rating || 0) < Number(filters.ratingMin)) return false;
    if (filters.distanceKm && Number(tailor.distanceKm ?? Number.POSITIVE_INFINITY) > Number(filters.distanceKm)) return false;
    if (filters.service) {
      const serviceNeedle = String(filters.service).toLowerCase();
      const services = (tailor.expertise || []).join(" ").toLowerCase();
      if (!services.includes(serviceNeedle)) return false;
    }
    if (!tokens.length) return true;
    const haystack = customerTailorSearchText(tailor);
    return tokens.every((token) => haystack.includes(token));
  });
}

function customerSearchSuggestions(rows, query) {
  const needle = String(query || "").trim().toLowerCase();
  if (!needle) return [];
  const suggestions = new Map();
  const add = (value, type) => {
    const label = String(value || "").trim();
    if (!label || !label.toLowerCase().includes(needle)) return;
    const key = `${type}:${label.toLowerCase()}`;
    if (!suggestions.has(key)) suggestions.set(key, { label, type });
  };

  rows.forEach((tailor) => {
    add(tailor.shop, "Tailor");
    add(tailor.ownerName, "Name");
    add(tailor.zoneId, "Location");
    add(tailor.shopAddress, "Location");
    (tailor.expertise || []).forEach((item) => add(item, "Service"));
    if (tailor.rating) add(`${Number(tailor.rating).toFixed(1)} rating`, "Rating");
  });

  return Array.from(suggestions.values()).slice(0, 8);
}

function CustomerApp({ onLogout }) {
  const t = useT();
  const [account, setAccount] = useState(null);
  const [tailors, setTailors] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [bookings, setBookings] = useState({ requests: [], orders: [], notifications: [] });
  const [filters, setFilters] = useState({ q: "", availability: "", ratingMin: "", service: "", distanceKm: "" });
  const [radiusKm, setRadiusKm] = useState(50);
  const [geo, setGeo] = useState({ latitude: null, longitude: null, status: "detecting", message: "Detecting your location..." });
  const [activePanel, setActivePanel] = useAppHistoryState("customerPanel", "browse");
  const [selected, setSelected] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load(nextGeo = geo, nextRadius = radiusKm) {
    setLoading(true);
    setError("");
    try {
      const hasLocation = nextGeo.latitude !== null && nextGeo.longitude !== null;
      const tailorsPromise = hasLocation
        ? api.nearbyTailors({ latitude: nextGeo.latitude, longitude: nextGeo.longitude, radius_km: nextRadius })
        : api.customerTailors({});
      const [nextTailorsRaw, nextBookings, nextFavorites, me] = await Promise.all([
        tailorsPromise,
        api.customerBookings(),
        api.customerFavorites(),
        api.me().catch(() => null),
      ]);
      const favoriteIds = new Set(nextFavorites.map((tailor) => tailor.id));
      const nextTailors = nextTailorsRaw.map((tailor) => ({
        ...tailor,
        favoritedByMe: tailor.favoritedByMe || favoriteIds.has(tailor.id),
      }));
      setTailors(nextTailors);
      setBookings(nextBookings);
      setFavorites(nextFavorites);
      if (me?.user) setAccount(me.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!navigator.geolocation) {
      const fallbackGeo = { latitude: null, longitude: null, status: "unavailable", message: "Location permission is unavailable. Showing approved tailors." };
      setGeo(fallbackGeo);
      load(fallbackGeo);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const nextGeo = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          status: "ready",
          message: "Nearby tailors sorted by distance from your current location.",
        };
        setGeo(nextGeo);
        load(nextGeo);
      },
      () => {
        const fallbackGeo = { latitude: null, longitude: null, status: "denied", message: "Location permission denied. Showing approved tailors." };
        setGeo(fallbackGeo);
        load(fallbackGeo);
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 300000 },
    );
  }, []);

  useEffect(() => {
    if (geo.status !== "ready" || geo.latitude === null || geo.longitude === null) return undefined;
    const timer = window.setTimeout(() => load(geo, radiusKm), 300);
    return () => window.clearTimeout(timer);
  }, [radiusKm, geo.latitude, geo.longitude, geo.status]);

  async function openProfile(tailor) {
    setSelected(tailor);
    setProfile(null);
    setActivePanel("profile");
    setError("");
    try {
      const [detail, priceList] = await Promise.all([
        api.customerTailor(tailor.id),
        api.publicTailorServices(tailor.id).catch(() => null),
      ]);
      setProfile({ ...detail, services: priceList || detail.services || [] });
      setSelected(detail.tailor);
    } catch (err) {
      setError(err.message);
    }
  }

  const unreadUpdates = unreadCount(bookings.notifications || []);
  const visibleTailors = useMemo(() => filterCustomerTailors(tailors, filters), [tailors, filters]);
  const customerDisplayName = account?.name || account?.fullName || "";
  const customerContact = account?.phone || account?.email || t("customer.findTrack", "Find and track tailoring");
  const customerHeaderTitle = customerDisplayName ? `Welcome, ${customerDisplayName}` : "Welcome";

  useEffect(() => {
    if (activePanel !== "updates" || !unreadUpdates) return;
    let cancelled = false;
    api.markCustomerNotificationsRead()
      .then(() => {
        if (cancelled) return;
        setBookings((old) => ({
          ...old,
          notifications: (old.notifications || []).map((row) => ({ ...row, read: true })),
        }));
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [activePanel, unreadUpdates]);

  function patchTailorState(nextTailor) {
    setTailors((rows) => rows.map((row) => row.id === nextTailor.id ? nextTailor : row));
    setFavorites((rows) => {
      if (!nextTailor.favoritedByMe) return rows.filter((row) => row.id !== nextTailor.id);
      return rows.some((row) => row.id === nextTailor.id) ? rows.map((row) => row.id === nextTailor.id ? nextTailor : row) : [nextTailor, ...rows];
    });
    setSelected((old) => old?.id === nextTailor.id ? nextTailor : old);
    setProfile((old) => old?.tailor?.id === nextTailor.id ? { ...old, tailor: nextTailor } : old);
  }

  async function toggleFavorite(tailor) {
    setError("");
    try {
      const res = tailor.favoritedByMe ? await api.unfavoriteTailor(tailor.id) : await api.favoriteTailor(tailor.id);
      patchTailorState(res.tailor);
      return res.tailor;
    } catch (err) {
      setError(err.message);
      return tailor;
    }
  }

  async function toggleFollow(tailor) {
    setError("");
    try {
      const res = tailor.followedByMe ? await api.unfollowTailor(tailor.id) : await api.followTailor(tailor.id);
      patchTailorState(res.tailor);
      return res.tailor;
    } catch (err) {
      setError(err.message);
      return tailor;
    }
  }

  async function handleBookingCreated(createdBooking) {
    if (createdBooking?.id) {
      setBookings((old) => {
        const existingOrders = old.orders || [];
        const nextOrders = existingOrders.some((row) => row.id === createdBooking.id)
          ? existingOrders.map((row) => row.id === createdBooking.id ? { ...row, ...createdBooking } : row)
          : [createdBooking, ...existingOrders];
        return { ...old, orders: nextOrders };
      });
    }
    setSelected(null);
    setProfile(null);
    setActivePanel("orders");
    await load();
  }

  const panels = [
    ["browse", t("customer.panel.browse", "Browse Tailors"), UsersRound, null],
    ["profile", t("customer.panel.profile", "Selected Tailor"), Scissors, null],
    ["favorites", t("common.favorites", "Favorites"), Heart, null],
    ["updates", t("common.updates", "Updates"), FileClock, unreadUpdates],
    ["wallet", t("common.wallet", "Wallet"), CreditCard, null],
    ["referrals", t("common.referrals", "Referrals"), UsersRound, null],
    ["requests", t("common.requests", "Requests"), ClipboardList, null],
    ["orders", t("common.orders", "Orders"), CreditCard, null],
    ["support", t("common.support", "Support"), AlertTriangle, null],
  ];

  return (
    <Shell title={customerHeaderTitle} subtitle={t("dashboard.customer.subtitle", "Browse and book approved tailors")} icon={UsersRound} onLogout={onLogout} actions={<button className="icon-btn" onClick={() => load()} title={t("common.refresh", "Refresh")}><RefreshCw size={17} /></button>}>
      {error ? <div className="error banner">{error}</div> : null}
      {loading ? <div className="loading">{t("customer.loading", "Loading customer data...")}</div> : null}
      <div className="customer-workspace">
        <aside className="customer-side-card">
          <div className="tailor-side-head">
            <CustomerAvatar customer={account || { name: customerDisplayName }} size="lg" />
            <div>
              <h3>{customerDisplayName || "Welcome"}</h3>
              <p>{selected ? selected.shop : customerContact}</p>
            </div>
          </div>
          <small>{selected ? `${t("customer.selected", "Selected")}: ${selected.ownerName}` : t("customer.chooseSection", "Choose a section to continue.")}</small>
          <nav className="tailor-side-nav">
            {panels.map(([id, label, Icon, count]) => (
              <button key={id} className={activePanel === id ? "active" : ""} onClick={() => setActivePanel(id)}>
                <Icon size={16} />
                <span>{label}</span>
                {count ? <b>{count}</b> : null}
              </button>
            ))}
          </nav>
        </aside>
        <div className="customer-content">
          {activePanel === "browse" ? <CustomerBrowsePanel filters={filters} setFilters={setFilters} allTailors={tailors} tailors={visibleTailors} openProfile={openProfile} onBook={openProfile} onFavorite={toggleFavorite} onFollow={toggleFollow} geo={geo} radiusKm={radiusKm} setRadiusKm={setRadiusKm} /> : null}
          {activePanel === "profile" ? (
            selected && profile ? <CustomerTailorProfile profile={profile} reload={load} onFavorite={toggleFavorite} onFollow={toggleFollow} onBookingCreated={handleBookingCreated} /> : <Empty text={t("customer.selectTailorEmpty", "Select a tailor from Browse Tailors to see profile, services, reviews, availability and booking form.")} />
          ) : null}
          {activePanel === "favorites" ? <CustomerFavoritesPanel tailors={favorites} openProfile={openProfile} onFavorite={toggleFavorite} onFollow={toggleFollow} /> : null}
          {activePanel === "updates" ? <Updates title={t("customer.updatesTitle", "Customer Updates")} rows={bookings.notifications || []} /> : null}
          {activePanel === "wallet" ? <CustomerWalletPanel /> : null}
          {activePanel === "referrals" ? <CustomerReferralPanel /> : null}
          {activePanel === "requests" ? <CustomerRequests rows={bookings.requests || []} /> : null}
          {activePanel === "orders" ? <CustomerOrders rows={bookings.orders || []} reload={load} /> : null}
          {activePanel === "support" ? <SupportPanel role="customer" orders={bookings.orders || []} /> : null}
        </div>
      </div>
    </Shell>
  );
}

function CustomerBrowsePanel({ filters, setFilters, allTailors, tailors, openProfile, onBook, onFavorite, onFollow, geo, radiusKm, setRadiusKm }) {
  const t = useT();
  const filterAreaRef = useRef(null);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [activeFilterGroup, setActiveFilterGroup] = useState("service");
  const suggestions = useMemo(() => customerSearchSuggestions(allTailors, filters.q), [allTailors, filters.q]);
  const activeFilterCount = [filters.service, filters.ratingMin, filters.distanceKm, filters.availability].filter(Boolean).length;
  const serviceOptions = [
    ["", "All services"],
    ["blouse", "Blouses"],
    ["shirt", "Shirts"],
    ["pant", "Pants"],
    ["alteration", "Alterations"],
    ["saree", "Sarees"],
    ["lehenga", "Lehengas"],
    ["kurta", "Kurtas"],
  ];
  const ratingOptions = [
    ["", "All ratings"],
    ["3", "3+ rating"],
    ["4", "4+ rating"],
    ["5", "5 rating"],
  ];
  const distanceOptions = [
    ["", "Any distance"],
    ["10", "Within 10 km"],
    ["20", "Within 20 km"],
    ["50", "Below 50 km"],
    ["100", "Below 100 km"],
  ];
  const availabilityOptions = [
    ["", t("customer.allAvailability", "All availability")],
    ["AVAILABLE", t("common.available", "Available")],
    ["FEW_SLOTS_AVAILABLE", t("common.fewSlots", "Few slots")],
    ["BUSY", t("common.busy", "Busy")],
    ["NOT_AVAILABLE", t("common.unavailable", "Unavailable")],
  ];
  const updateFilter = (next) => setFilters((old) => ({ ...old, ...next }));
  function updateDistanceFilter(value) {
    updateFilter({ distanceKm: value });
    if (geo.status === "ready") setRadiusKm(value ? Number(value) : 50);
  }
  function clearBrowseFilters() {
    updateFilter({ service: "", ratingMin: "", distanceKm: "", availability: "" });
    if (geo.status === "ready") setRadiusKm(50);
  }
  const filterGroups = [
    { key: "service", label: "Service", value: filters.service, options: serviceOptions, onSelect: (value) => updateFilter({ service: value }) },
    { key: "rating", label: "Rating", value: filters.ratingMin, options: ratingOptions, onSelect: (value) => updateFilter({ ratingMin: value }) },
    { key: "distance", label: "Distance", value: filters.distanceKm, options: distanceOptions, onSelect: updateDistanceFilter },
    { key: "availability", label: "Availability", value: filters.availability, options: availabilityOptions, onSelect: (value) => updateFilter({ availability: value }) },
  ];
  const activeGroup = filterGroups.find((group) => group.key === activeFilterGroup) || filterGroups[0];
  const selectedLabel = (group) => group.options.find(([value]) => value === group.value)?.[1] || "";

  useEffect(() => {
    if (!filtersOpen) return undefined;
    function closeOnOutsideClick(event) {
      if (filterAreaRef.current?.contains(event.target)) return;
      setFiltersOpen(false);
    }
    window.addEventListener("pointerdown", closeOnOutsideClick);
    return () => window.removeEventListener("pointerdown", closeOnOutsideClick);
  }, [filtersOpen]);

  return (
    <section className="section-block no-top">
      <section className={filtersOpen ? "toolbar customer-live-toolbar filter-open" : "toolbar customer-live-toolbar"}>
        <div className="live-search-wrap" ref={filterAreaRef}>
          <div className="live-search-line">
            <label className="search live-search">
              <Search size={16} />
              <input
                value={filters.q}
                onChange={(e) => {
                  updateFilter({ q: e.target.value });
                  setSuggestionsOpen(true);
                }}
                onFocus={() => setSuggestionsOpen(true)}
                onBlur={() => window.setTimeout(() => setSuggestionsOpen(false), 120)}
                placeholder={t("customer.searchPlaceholder", "Search tailor, service, location, rating")}
              />
            </label>
            <button
              type="button"
              className={filtersOpen ? "filter-menu-btn active" : "filter-menu-btn"}
              onClick={() => setFiltersOpen((open) => !open)}
              aria-label="Search filters"
              aria-expanded={filtersOpen}
              title="Filters"
            >
              <span>Filters</span>
              {activeFilterCount ? <b>{activeFilterCount}</b> : null}
            </button>
          </div>
          {suggestionsOpen && suggestions.length ? (
            <div className="search-suggestions">
              {suggestions.map((item) => (
                <button
                  type="button"
                  key={`${item.type}-${item.label}`}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    updateFilter({ q: item.label });
                    setSuggestionsOpen(false);
                  }}
                >
                  <span>{item.label}</span>
                  <small>{item.type}</small>
                </button>
              ))}
            </div>
          ) : null}
          {filtersOpen ? (
          <aside className="filter-side-panel" aria-label="Browse filters">
            <div className="filter-side-head">
              <div>
                <strong>Filters</strong>
                <small>{geo.status === "ready" ? `Radius ${radiusKm} km` : "Distance needs location access"}</small>
              </div>
              {activeFilterCount ? <button type="button" className="filter-clear-btn" onClick={clearBrowseFilters}>Clear</button> : null}
            </div>
            <div className="filter-side-body">
              <div className="filter-groups" role="tablist" aria-label="Filter categories">
                {filterGroups.map((group) => (
                  <button
                    type="button"
                    key={group.key}
                    className={activeGroup.key === group.key ? "active" : ""}
                    onClick={() => setActiveFilterGroup(group.key)}
                  >
                    <span>{group.label}</span>
                    {group.value ? <small>{selectedLabel(group)}</small> : null}
                  </button>
                ))}
              </div>
              <div className="filter-options" role="group" aria-label={`${activeGroup.label} options`}>
                <span>{activeGroup.label}</span>
                <div className="availability-filter compact">
                  {activeGroup.options.map(([value, label]) => (
                    <button
                      type="button"
                      key={value || `all-${activeGroup.key}`}
                      className={activeGroup.value === value ? "active" : ""}
                      onClick={() => activeGroup.onSelect(value)}
                      disabled={activeGroup.key === "distance" && geo.status !== "ready" && Boolean(value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </aside>
          ) : null}
        </div>
      </section>
      <small className="filter-result-count">{tailors.length} tailor{tailors.length === 1 ? "" : "s"} match your filters.</small>
      <h3>{geo.status === "ready" ? t("customer.nearbyTailors", "Nearby Tailors") : t("customer.approvedTailors", "Approved Tailors")}</h3>
      <PaginatedCards
        items={tailors}
        pageSize={6}
        label="tailors"
        emptyText={t("customer.noTailors", "No approved tailors match the current filters. Clear filters or approve a tailor from Admin.")}
        renderItem={(tailor) => <TailorCard tailor={tailor} onOpen={() => openProfile(tailor)} onBook={() => onBook(tailor)} onFavorite={onFavorite} onFollow={onFollow} />}
      />
    </section>
  );
}

function CustomerFavoritesPanel({ tailors, openProfile, onFavorite, onFollow }) {
  const t = useT();
  return (
    <section className="section-block no-top">
      <h3>{t("customer.favoriteTailors", "Favorite Tailors")}</h3>
      <PaginatedCards
        items={tailors}
        pageSize={6}
        label="favorites"
        emptyText={t("customer.noFavorites", "No favorite tailors yet. Tap the heart on a tailor you like.")}
        renderItem={(tailor) => <TailorCard tailor={tailor} onOpen={() => openProfile(tailor)} onBook={() => openProfile(tailor)} onFavorite={onFavorite} onFollow={onFollow} />}
      />
    </section>
  );
}

function TailorCard({ tailor, onOpen, onBook, onFavorite, onFollow }) {
  const t = useT();
  const disabled = tailor.availability === "NOT_AVAILABLE" || !tailor.acceptingRequests;
  const firstMedia = portfolioItems(tailor.portfolio)[0];
  return (
    <article className="record-card tailor-card">
      <div className="tailor-card-cover">
        {firstMedia ? (
          firstMedia.kind === "video" ? <video src={firstMedia.url} muted preload="metadata" /> : <img src={firstMedia.url} alt={`${tailor.shop} cover`} />
        ) : (
          <div className="tailor-cover-fallback">
            <Scissors size={28} />
            <span>TailoraHub Atelier</span>
          </div>
        )}
        <button className={tailor.favoritedByMe ? "cover-favorite active" : "cover-favorite"} onClick={() => onFavorite(tailor)} title={tailor.favoritedByMe ? t("customer.removeFavorite", "Remove favorite") : t("customer.addFavorite", "Add favorite")}>
          <Heart size={18} />
        </button>
      </div>
      <div className="tailor-card-profile-row">
        <TailorAvatar tailor={tailor} size="lg" />
        <div className="tailor-verify-slot">
          {tailor.verified ? <BadgeCheck size={19} /> : null}
        </div>
      </div>
      <div className="tailor-card-body">
        <div className="tailor-card-title">
          <h3>{tailor.shop}</h3>
          <p>{tailor.ownerName} - {tailor.zoneId}</p>
        </div>
        <div className="rating"><Star size={15} /> {Number(tailor.rating || 0).toFixed(1)} ({tailor.ratingCount || 0})</div>
        <p>{(tailor.expertise || []).join(", ") || "Custom stitching"}</p>
        <div className="relationship-row">
          <button className={tailor.favoritedByMe ? "mini-action active" : "mini-action"} onClick={() => onFavorite(tailor)} title={tailor.favoritedByMe ? t("customer.removeFavorite", "Remove favorite") : t("customer.addFavorite", "Add favorite")}>
            <Heart size={15} />
            <span>{tailor.favoritedByMe ? t("customer.favorited", "Favorited") : t("common.favorites", "Favorite")}</span>
            <b>{tailor.favoriteCount || 0}</b>
          </button>
          <button className={tailor.followedByMe ? "mini-action active" : "mini-action"} onClick={() => onFollow(tailor)} title={tailor.followedByMe ? t("customer.unfollow", "Unfollow tailor") : t("customer.followTailor", "Follow tailor")}>
            <Bell size={15} />
            <span>{tailor.followedByMe ? t("customer.following", "Following") : t("customer.follow", "Follow")}</span>
            <b>{tailor.followerCount || 0}</b>
          </button>
        </div>
        <div className="meta-grid">
          <span>{t("tailor.completedOrders", "Completed")} <b>{tailor.completed || 0}</b></span>
          <span>{t("customer.fromPrice", "From")} <b>{money(tailor.startingPrice)}</b></span>
          <span>{tailor.distanceKm !== undefined ? t("customer.distance", "Distance") : t("status.ACTIVE", "Active")} <b>{tailor.distanceKm !== undefined ? `${Number(tailor.distanceKm).toFixed(1)} km` : tailor.activeOrders || 0}</b></span>
        </div>
        {tailor.experienceDisplay !== undefined ? <small>{t("customer.experience", "Experience")}: {Number(tailor.experienceDisplay || 0).toFixed(1)} {t("customer.years", "years")}</small> : null}
        <StatusPill value={tailor.availability} />
        <small>{t(`availability.${tailor.availability}`, availabilityCopy[tailor.availability] || "Availability not updated")}</small>
        {tailor.nextAvailable ? <small>{t("tailor.nextAvailable", "Next available")}: {fmtDay(tailor.nextAvailable)}</small> : null}
        {disabled ? <div className="notice">{t("availability.NOT_AVAILABLE", "Currently Not Accepting New Orders")}</div> : null}
        <div className="inline-actions">
          <button className="secondary-btn" onClick={onOpen}>{t("customer.viewProfile", "View Profile")}</button>
          <button className="primary-btn compact-action" onClick={onBook}>{t("customer.book", "Book")}</button>
        </div>
      </div>
    </article>
  );
}

function OfferList({ offers = [], onRemove }) {
  return (
    <ViewMoreGrid
      items={offers}
      initial={4}
      step={4}
      className="offer-grid"
      label="offers"
      emptyText="No active offers posted yet."
      renderItem={(offer) => {
        const mediaUrl = assetUrl(offer.mediaUrl);
        const mediaKind = mediaKindFrom(offer.mediaType, mediaUrl);
        return (
          <article className={offer.active === false ? "offer-card inactive" : "offer-card"} key={offer.id}>
            {mediaUrl ? (
              <div className="offer-media">
                {mediaKind === "video" ? <video src={mediaUrl} controls preload="metadata" /> : <img src={mediaUrl} alt={offer.title} />}
              </div>
            ) : null}
            <div>
              <h3>{offer.title}</h3>
              <p>{offer.body}</p>
              {offer.discount ? <span className="offer-badge">{offer.discount}</span> : null}
              <small>{offer.expiresAt ? `Valid until ${fmtDay(offer.expiresAt)}` : `Posted ${fmtDate(offer.createdAt)}`}</small>
            </div>
            {onRemove && offer.active !== false ? <button className="danger-link" type="button" onClick={() => onRemove(offer.id)}>Deactivate</button> : null}
          </article>
        );
      }}
    />
  );
}

function normalizeService(row) {
  const id = row?.id || row?.serviceId || row?.service_id || "";
  return {
    ...row,
    id,
    serviceId: row?.serviceId || id,
    serviceUuid: row?.serviceUuid || row?.service_id || "",
    name: row?.name || row?.serviceName || row?.service_name || "Service",
    category: row?.category || "Other",
    price: row?.price || 0,
    days: row?.days || 5,
    garmentId: row?.garmentId || row?.garment_id || null,
    description: row?.description || "",
    isCombo: Boolean(row?.isCombo ?? row?.is_combo),
    comboItems: row?.comboItems || row?.combo_items || [],
    isActive: Boolean(row?.isActive ?? row?.is_active ?? true),
  };
}

function servicePatchId(service) {
  return service.serviceUuid || service.service_id || service.serviceId || service.id;
}

function CustomerTailorProfile({ profile, reload, onFavorite, onFollow, onBookingCreated }) {
  const { tailor, services, reviews, offers = [] } = profile;
  const serviceRows = useMemo(() => (services || []).map(normalizeService), [services]);
  const [serviceId, setServiceId] = useState(serviceRows[0]?.id || "");
  const [form, setForm] = useState({ quantity: 1, requirements: "", preferredDate: "", instructions: "", measurementMode: "customer_visits_tailor", homeLocation: null, appointmentDate: "", appointmentSlot: "" });
  const [showHomeMap, setShowHomeMap] = useState(false);
  const [message, setMessage] = useState("");
  const disabled = tailor.availability === "NOT_AVAILABLE" || !tailor.acceptingRequests;
  const latestAppointmentDate = useMemo(() => measurementAppointmentLatestDate(form.preferredDate), [form.preferredDate]);
  const selectedService = useMemo(() => serviceRows.find((s) => s.id === serviceId) || serviceRows[0], [serviceRows, serviceId]);
  const bookingQuantity = Math.max(1, Number(form.quantity || 1));
  const serviceAmount = Number(selectedService?.price || 0) * bookingQuantity;
  const travelDistanceKm = form.measurementMode === "tailor_visits_customer" && form.homeLocation
    ? estimateTravelDistanceKm(tailor, form.homeLocation)
    : 0;
  const travelCharge = form.measurementMode === "tailor_visits_customer" && form.homeLocation
    ? Math.round(travelDistanceKm * TRAVEL_CHARGE_PER_KM)
    : 0;
  const orderSubtotal = serviceAmount + travelCharge;
  const gstPlatformEstimate = Math.round((orderSubtotal * BOOKING_TAX_ESTIMATE_PERCENTAGE) / 100);
  const bookingEstimateTotal = orderSubtotal + gstPlatformEstimate;

  useEffect(() => {
    setServiceId(serviceRows[0]?.id || "");
  }, [tailor.id, serviceRows]);

  function update(key, value) {
    setForm((old) => {
      const next = { ...old, [key]: value };
      if (key === "preferredDate" && old.appointmentDate && !isMeasurementAppointmentAllowed(old.appointmentDate, value)) {
        next.appointmentDate = "";
      }
      if (key === "measurementMode" && value !== "tailor_visits_customer") {
        next.homeLocation = null;
      }
      return next;
    });
  }

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    const service = selectedService || serviceRows.find((s) => s.id === serviceId);
    const today = todayDateInput();
    if (!form.preferredDate) {
      setMessage("Choose expected delivery date first.");
      return;
    }
    if (form.preferredDate < today) {
      setMessage("Expected delivery date cannot be in the past. Choose today or a future date.");
      return;
    }
    if (!form.appointmentDate) {
      setMessage("Choose measurement appointment date.");
      return;
    }
    if (form.appointmentDate < today) {
      setMessage("Measurement appointment cannot be in the past. Choose today or a future date.");
      return;
    }
    if (!isMeasurementAppointmentAllowed(form.appointmentDate, form.preferredDate)) {
      setMessage(MEASUREMENT_APPOINTMENT_ERROR);
      return;
    }
    if (form.measurementMode === "tailor_visits_customer" && !form.homeLocation) {
      setMessage("Confirm your home location before booking. Use the map pin and click Confirm this location.");
      return;
    }
    try {
      const res = await api.createBooking({
        tailorId: tailor.tailorId || tailor.id,
        serviceId,
        serviceName: service?.name,
        quantity: Number(form.quantity || 1),
        requirements: form.requirements,
        preferredDate: form.preferredDate || null,
        instructions: form.instructions,
        measurementMode: form.measurementMode,
        appointmentDate: form.appointmentDate || null,
        appointmentSlot: form.appointmentSlot,
        customerLocationAddress: form.measurementMode === "tailor_visits_customer" ? form.homeLocation?.address_text : undefined,
        customerLocationLat: form.measurementMode === "tailor_visits_customer" ? form.homeLocation?.latitude : undefined,
        customerLocationLng: form.measurementMode === "tailor_visits_customer" ? form.homeLocation?.longitude : undefined,
      });
      setMessage(res.message || `Booking ${res.code} created with ${tailor.shop}.`);
      setForm({ quantity: 1, requirements: "", preferredDate: "", instructions: "", measurementMode: "customer_visits_tailor", homeLocation: null, appointmentDate: "", appointmentSlot: "" });
      setShowHomeMap(false);
      if (onBookingCreated) {
        await onBookingCreated(res.booking || res);
      } else {
        await reload();
      }
    } catch (err) {
      setMessage(err.message);
    }
  }

  return (
    <div className="profile-panel">
      <div className="profile-heading">
        <TailorAvatar tailor={tailor} size="lg" />
        <div>
          <h3>{tailor.shop}</h3>
          <p>{tailor.ownerName} - {tailor.years} years experience</p>
        </div>
      </div>
      <div className="relationship-row profile-actions">
        <button className={tailor.favoritedByMe ? "mini-action active" : "mini-action"} type="button" onClick={() => onFavorite(tailor)} title={tailor.favoritedByMe ? "Remove favorite" : "Add favorite"}>
          <Heart size={15} />
          <span>{tailor.favoritedByMe ? "Favorited" : "Favorite"}</span>
          <b>{tailor.favoriteCount || 0}</b>
        </button>
        <button className={tailor.followedByMe ? "mini-action active" : "mini-action"} type="button" onClick={() => onFollow(tailor)} title={tailor.followedByMe ? "Unfollow tailor" : "Follow tailor"}>
          <Bell size={15} />
          <span>{tailor.followedByMe ? "Following" : "Follow"}</span>
          <b>{tailor.followerCount || 0}</b>
        </button>
      </div>
      <StatusPill value={tailor.availability} />
      <p>{tailor.availabilityNote || availabilityCopy[tailor.availability]}</p>
      <p>{tailor.bio || "No profile description yet."}</p>
      <h3>Offers</h3>
      <OfferList offers={offers} />
      <h3>Photos and Videos</h3>
      <MediaGallery portfolio={tailor.portfolio} />
      <h3>Services</h3>
      <PaginatedCards
        items={serviceRows}
        pageSize={5}
        className="service-list"
        label="services"
        emptyText="No active services added yet."
        renderItem={(s) => (
          <button className={serviceId === s.id ? "service active" : "service"} onClick={() => setServiceId(s.id)}>
            <span>{s.name}</span>
            <b>{money(s.price)}</b>
            <small>{s.category}{s.isCombo && s.comboItems.length ? ` - Includes ${s.comboItems.join(", ")}` : ""}</small>
            {s.description ? <small>{s.description}</small> : null}
          </button>
        )}
      />
      <h3>Send Booking Request</h3>
      {disabled ? <div className="notice">Currently Not Accepting New Orders</div> : (
        <form className="stack-form" onSubmit={submit}>
          <label>Quantity<input type="number" min="1" value={form.quantity} onChange={(e) => update("quantity", e.target.value)} /></label>
          <label>Stitching requirements<textarea value={form.requirements} onChange={(e) => update("requirements", e.target.value)} /></label>
          <label>Expected delivery date<input type="date" value={form.preferredDate} min={todayDateInput()} onChange={(e) => update("preferredDate", e.target.value)} required /></label>
          <label>
            Measurement method
            <select
              value={form.measurementMode}
              onChange={(e) => {
                const nextMode = e.target.value;
                update("measurementMode", nextMode);
                setShowHomeMap(nextMode === "tailor_visits_customer" && !form.homeLocation);
              }}
            >
              <option value="customer_visits_tailor">Customer visits tailor</option>
              <option value="tailor_visits_customer">Tailor visits customer</option>
            </select>
          </label>
          {form.measurementMode === "tailor_visits_customer" ? (
            <div className={form.homeLocation && !showHomeMap ? "booking-map booking-map-collapsed span-2" : "booking-map span-2"}>
              {form.homeLocation && !showHomeMap ? (
                <div className="booking-location-picked">
                  <div>
                    <span>Location picked</span>
                    <strong>{form.homeLocation.address_text || "Pinned home location"}</strong>
                    <small>{finiteNumber(form.homeLocation.latitude)?.toFixed(5)}, {finiteNumber(form.homeLocation.longitude)?.toFixed(5)}</small>
                  </div>
                  <button type="button" className="secondary-btn" onClick={() => setShowHomeMap(true)}>Change location</button>
                </div>
              ) : (
                <>
                  <MapPicker
                    initialLocation={form.homeLocation || {}}
                    onConfirm={(location) => {
                      update("homeLocation", location);
                      setShowHomeMap(false);
                    }}
                  />
                  {form.homeLocation ? <div className="notice ok">Home location confirmed for this booking only.</div> : <div className="notice">Confirm your exact home location before booking.</div>}
                </>
              )}
            </div>
          ) : <div className="notice">Visit shop: {tailor.shopAddress || tailor.zoneId}</div>}
          <BookingEstimateCard
            serviceName={selectedService?.name || "Selected service"}
            serviceAmount={serviceAmount}
            quantity={bookingQuantity}
            measurementMode={form.measurementMode}
            travelDistanceKm={travelDistanceKm}
            travelCharge={travelCharge}
            gstPlatformEstimate={gstPlatformEstimate}
            total={bookingEstimateTotal}
            needsLocation={form.measurementMode === "tailor_visits_customer" && !form.homeLocation}
          />
          <label>
            Measurement appointment date
            <input
              type="date"
              value={form.appointmentDate}
              min={todayDateInput()}
              max={latestAppointmentDate || undefined}
              onChange={(e) => update("appointmentDate", e.target.value)}
              required
            />
            <small>{latestAppointmentDate ? "Choose before the final 2-day delivery window." : "Choose expected delivery date first."}</small>
          </label>
          <label>Appointment time<input value={form.appointmentSlot} onChange={(e) => update("appointmentSlot", e.target.value)} placeholder="10:30 AM" /></label>
          <label>Special instructions<textarea value={form.instructions} onChange={(e) => update("instructions", e.target.value)} /></label>
          <button className="primary-btn">Send Request</button>
        </form>
      )}
      {message ? <div className={message.includes("waiting list") ? "notice waiting-notice" : message.includes("Booking") || message.includes("approved") ? "notice ok" : "error"}>{message.includes("waiting list") ? <><span className="live-dot" /> {message}</> : message}</div> : null}
      <h3>Reviews</h3>
      <ViewMoreGrid
        items={reviews}
        initial={4}
        step={4}
        className="review-list"
        label="reviews"
        emptyText="No public reviews yet."
        renderItem={(review) => <ReviewCard review={review} />}
      />
    </div>
  );
}

function BookingEstimateCard({
  serviceName,
  serviceAmount,
  quantity,
  measurementMode,
  travelDistanceKm,
  travelCharge,
  gstPlatformEstimate,
  total,
  needsLocation,
}) {
  return (
    <div className="booking-estimate-card span-2">
      <div className="booking-estimate-head">
        <div>
          <span>Payment details</span>
          <strong>{serviceName}</strong>
        </div>
        <b>{money(total)}</b>
      </div>
      <div className="booking-estimate-row">
        <span>Service amount x {quantity}</span>
        <strong>{money(serviceAmount)}</strong>
      </div>
      <div className="booking-estimate-row">
        <span>
          Home visit travel
          {measurementMode === "tailor_visits_customer" && !needsLocation ? ` (${travelDistanceKm.toFixed(1)} km x Rs ${TRAVEL_CHARGE_PER_KM})` : ""}
        </span>
        <strong>{measurementMode === "tailor_visits_customer" ? needsLocation ? "Pick location" : money(travelCharge) : "Not applicable"}</strong>
      </div>
      <div className="booking-estimate-row">
        <span>GST + platform estimate</span>
        <strong>{money(gstPlatformEstimate)}</strong>
      </div>
      <div className="booking-estimate-row total">
        <span>Total payable at payment</span>
        <strong>{money(total)}</strong>
      </div>
      <small>Final GST/platform values are confirmed again at Razorpay payment time.</small>
    </div>
  );
}

function ReviewCard({ review }) {
  const rating = Number(review.rating || 0);
  return (
    <article className="review">
      <div className="review-head">
        <div>
          <strong>{review.customer_name || "Customer"}</strong>
          <small>Verified completed order</small>
        </div>
        <div className="review-rating" aria-label={`${rating.toFixed(1)} star rating`}>
          {[1, 2, 3, 4, 5].map((value) => (
            <Star key={value} size={15} className={value <= Math.round(rating) ? "filled" : ""} />
          ))}
          <b>{rating.toFixed(1)}</b>
        </div>
      </div>
      <p>{review.body || "Customer rated this order without a written comment."}</p>
      <small>{fmtDate(review.ts)}</small>
    </article>
  );
}

function CustomerWalletPanel() {
  const t = useT();
  const [wallet, setWallet] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setMessage("");
    try {
      setWallet(await api.customerWallet());
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) {
    return <section className="section-block no-top"><div className="loading">{t("wallet.loading", "Loading wallet...")}</div></section>;
  }

  return (
    <section className="section-block no-top">
      <div className="section-head">
        <div>
          <h3>{t("common.wallet", "Wallet")}</h3>
          <p>{t("customer.walletDescription", "Refunds and admin-approved credits are held here for your customer account.")}</p>
        </div>
        <button type="button" className="secondary-btn" onClick={load}>{t("common.refresh", "Refresh")}</button>
      </div>
      {message ? <div className="error banner">{message}</div> : null}
      <div className="wallet-layout">
        <div className="wallet-card">
          <div>
            <small>Available balance</small>
            <strong>{money(wallet?.balance)}</strong>
            <span>Wallet ID {String(wallet?.wallet_id || "").slice(0, 8)}...</span>
          </div>
          <div className="wallet-qr-tile">
            <CreditCard size={44} />
            <span>Customer wallet</span>
          </div>
        </div>
        <div className="record-card">
          <h3>{t("customer.reservedCredits", "Reserved Credits")}</h3>
          <p>Admin-approved dispute refunds and future credits appear in this balance. Referral wallet rewards are paused for now.</p>
          <small>Last updated: {fmtDate(wallet?.updated_at || wallet?.updatedAt)}</small>
        </div>
      </div>
    </section>
  );
}

function CustomerReferralPanel() {
  const t = useT();
  const [referral, setReferral] = useState(null);
  const [count, setCount] = useState(0);
  const [bonus, setBonus] = useState(0);
  const [rewardsEnabled, setRewardsEnabled] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setMessage("");
    try {
      const [codeData, countData] = await Promise.all([
        api.customerReferralCode(),
        api.customerReferralCount(),
      ]);
      setReferral(codeData);
      setCount(countData.valid_count ?? countData.validCount ?? 0);
      setBonus(countData.bonus_amount ?? countData.bonusAmount ?? 0);
      setRewardsEnabled(Boolean(countData.rewards_enabled ?? countData.rewardsEnabled));
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function copyReferral(value) {
    setMessage("");
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(value);
      setMessage("Referral link copied.");
    } catch {
      setMessage("Copy is blocked in this browser. Select the link and copy it manually.");
    }
  }

  const code = referral?.referral_code || referral?.referralCode || "";
  const link = referral?.shareable_link || referral?.shareableLink || "";

  if (loading) {
    return <section className="section-block no-top"><div className="loading">{t("referrals.loading", "Loading referrals...")}</div></section>;
  }

  return (
    <section className="section-block no-top">
      <div className="section-head">
        <div>
          <h3>{t("common.referrals", "Referrals")}</h3>
          <p>{t("customer.referralHelp", "Valid referrals count only when the new customer registers with a brand-new mobile number.")}</p>
        </div>
        <button type="button" className="secondary-btn" onClick={load}>{t("common.refresh", "Refresh")}</button>
      </div>
      {message ? <div className={message.includes("copied") ? "notice ok" : "notice"}>{message}</div> : null}
      <div className="referral-summary-grid">
        <div className="referral-card referral-code-card">
          <span>{t("customer.referralCode", "Your referral code")}</span>
          <strong>{code || "-"}</strong>
          <button type="button" className="secondary-btn" onClick={() => copyReferral(code)} disabled={!code}>Copy Code</button>
        </div>
        <div className="referral-card">
          <span>{t("customer.validReferrals", "Valid referrals")}</span>
          <strong>{count}</strong>
          <small>{rewardsEnabled ? `${money(bonus)} bonus tracked for future use` : "Wallet rewards are paused; referrals are tracked only."}</small>
        </div>
      </div>
      <div className="record-card referral-share-card">
        <h3>{t("referrals.shareableLink", "Shareable Link")}</h3>
        <div className="share-link-row">
          <input readOnly value={link} aria-label="Customer referral link" />
          <button type="button" className="primary-btn" onClick={() => copyReferral(link)} disabled={!link}>Copy Link</button>
        </div>
      </div>
    </section>
  );
}

function CustomerRequests({ rows }) {
  return (
    <section className="section-block no-top">
      <h3>Requests</h3>
      {rows.length ? <Table columns={["Request", "Tailor", "Status", "Service", "Preferred"]} rows={rows.map((r) => [r.requirement_code, r.shop, <StatusPill value={r.status} />, r.tailor_service_name || r.service_name, fmtDay(r.preferred_date)])} /> : <Empty />}
    </section>
  );
}

function CustomerOrders({ rows, reload }) {
  const [filter, setFilter] = useState("in_progress");
  const inProgressOrders = rows.filter((order) => !isClosedOrder(order) && !isCancelledCustomerOrder(order));
  const completedOrders = rows.filter((order) => isClosedOrder(order) && !isCancelledCustomerOrder(order));
  const cancelledOrders = rows.filter((order) => isCancelledCustomerOrder(order));
  const filters = [
    ["in_progress", "In progress", inProgressOrders],
    ["completed", "Completed", completedOrders],
    ["cancelled", "Cancelled", cancelledOrders],
    ["all", "All orders", rows],
  ];
  const activeFilter = filters.find(([key]) => key === filter) || filters[0];
  const activeRows = activeFilter[2];

  return (
    <section className="section-block no-top">
      <div className="section-head">
        <div>
          <h3>Orders</h3>
          <p>Track active orders, review completed orders, or check cancelled orders.</p>
        </div>
      </div>
      {rows.length ? (
        <>
          <div className="order-filter-tabs" role="tablist" aria-label="Order filters">
            {filters.map(([key, label, items]) => (
              <button
                type="button"
                key={key}
                className={filter === key ? "active" : ""}
                onClick={() => setFilter(key)}
                role="tab"
                aria-selected={filter === key}
              >
                <span>{label}</span>
                <b>{items.length}</b>
              </button>
            ))}
          </div>
          {filter === "all" ? (
            <div className="order-card-list">
              <CustomerOrderGroup title="In progress orders" rows={inProgressOrders} emptyText="No in-progress orders right now." reload={reload} />
              <CustomerOrderGroup title="Completed orders" rows={completedOrders} emptyText="No completed orders yet." reload={reload} />
              <CustomerOrderGroup title="Cancelled orders" rows={cancelledOrders} emptyText="No cancelled orders." reload={reload} />
            </div>
          ) : (
            <CustomerOrderGroup title={`${activeFilter[1]} orders`} rows={activeRows} emptyText={`No ${activeFilter[1].toLowerCase()} orders right now.`} reload={reload} />
          )}
        </>
      ) : <Empty />}
    </section>
  );
}

function CustomerOrderGroup({ title, rows, emptyText, reload }) {
  return (
    <section className="customer-order-group">
      <div className="section-head tight">
        <div>
          <h3>{title}</h3>
          <p>{rows.length} order{rows.length === 1 ? "" : "s"}</p>
        </div>
      </div>
      {rows.length ? (
        <PaginatedCards
          items={rows}
          pageSize={4}
          className="customer-order-card-list"
          label="orders"
          emptyText={emptyText}
          renderItem={(order) => <CustomerOrderCard order={order} reload={reload} />}
        />
      ) : <Empty text={emptyText} />}
    </section>
  );
}

function trackerSocketUrl(orderId) {
  return `${api.base.replace(/^http/, "ws")}/v1/bookings/${encodeURIComponent(orderId)}/track`;
}

function normalizeOrderStatusPayload(order, statusPayload) {
  const booking = statusPayload?.booking || {};
  const stage = statusPayload?.trackerStage || booking.trackerStage || order.trackerStage || order.tracker_stage || "Order Placed";
  const steps = statusPayload?.steps || bookingTrackerStages.map((name, index) => {
    const currentIndex = bookingTrackerStages.indexOf(stage);
    return { stage: name, completed: index < currentIndex, current: index === currentIndex, timestamp: null };
  });
  return {
    ...order,
    ...booking,
    payment_status: booking.payment_status || booking.paymentStatus || order.payment_status,
    paymentStatus: booking.paymentStatus || booking.payment_status || order.paymentStatus,
    completed_at: booking.completed_at || booking.completedAt || order.completed_at,
    completedAt: booking.completedAt || booking.completed_at || order.completedAt,
    rated: Boolean(booking.rated ?? order.rated),
    trackerStage: stage,
    steps,
    otpEnabled: statusPayload?.otpEnabled ?? String(booking.paymentStatus || order.payment_status || "").toLowerCase() === "paid",
    paymentIntent: statusPayload?.paymentIntent || statusPayload?.payment_intent || booking.paymentIntent || booking.payment_intent || order.paymentIntent || order.payment_intent || null,
  };
}

function isClosedOrder(order) {
  return String(order?.status || "").toLowerCase() === "completed" || Boolean(order?.completed_at || order?.completedAt);
}

function isCancelledCustomerOrder(order) {
  return String(order?.status || "").toLowerCase() === "cancelled";
}

function orderDateInput(value) {
  if (!value) return "";
  const raw = String(value);
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(0, 10);
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "" : utcDateToDateInput(parsed);
}

function todayDateInput() {
  const today = new Date();
  return [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");
}

function laterDateInput(...values) {
  return values.filter(Boolean).sort().at(-1) || "";
}

function isCustomerManageAllowed(order) {
  if (order?.canCustomerManage === false) return false;
  if (isClosedOrder(order) || isCancelledCustomerOrder(order)) return false;
  const status = String(order?.status || "").toLowerCase();
  const stage = String(order?.trackerStage || order?.tracker_stage || "").toLowerCase();
  if (["measurement_done", "in_progress", "ready_for_delivery", "out_for_delivery", "disputed"].includes(status)) return false;
  if (["measurement done", "stitching in progress", "ready for delivery", "out for delivery", "delivered"].includes(stage)) return false;
  if (order?.measurement_done_at || order?.measurementDoneAt) return false;
  const appointmentDate = orderDateInput(order?.appointmentDate || order?.appointment_date);
  return !appointmentDate || todayDateInput() < appointmentDate;
}

let razorpayCheckoutPromise = null;

function loadRazorpayCheckout() {
  if (window.Razorpay) return Promise.resolve(window.Razorpay);
  if (!razorpayCheckoutPromise) {
    razorpayCheckoutPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => {
        if (window.Razorpay) resolve(window.Razorpay);
        else reject(new Error("Razorpay checkout could not be loaded."));
      };
      script.onerror = () => reject(new Error("Razorpay checkout could not be loaded. Check your internet connection."));
      document.body.appendChild(script);
    });
  }
  return razorpayCheckoutPromise;
}

async function openRazorpayCheckout(options) {
  const Razorpay = await loadRazorpayCheckout();
  return new Promise((resolve, reject) => {
    const checkout = new Razorpay({
      key: options.keyId || options.key_id,
      amount: options.amountPaise || options.amount_paise || options.amount,
      currency: options.currency || "INR",
      name: options.name || "TailoraHub",
      description: options.description || "TailoraHub order payment",
      order_id: options.razorpayOrderId || options.razorpay_order_id,
      prefill: options.prefill || {},
      notes: options.notes || {},
      theme: options.theme || { color: "#d4af37" },
      handler: resolve,
      modal: {
        ondismiss: () => reject(new Error("Payment window was closed before completion.")),
      },
    });
    checkout.on("payment.failed", (response) => {
      reject(new Error(response?.error?.description || "Razorpay payment failed. Please try again."));
    });
    checkout.open();
  });
}

function CustomerOrderCard({ order, reload }) {
  const [statusData, setStatusData] = useState(() => normalizeOrderStatusPayload(order, null));
  const [breakdown, setBreakdown] = useState(null);
  const [paymentIntent, setPaymentIntent] = useState(order.paymentIntent || order.payment_intent || null);
  const [activeView, setActiveView] = useState("");
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadStatus() {
    try {
      const payload = await api.bookingStatus(order.id);
      const nextStatus = normalizeOrderStatusPayload(order, payload);
      setStatusData(nextStatus);
      if (nextStatus.paymentIntent) setPaymentIntent(nextStatus.paymentIntent);
    } catch {
      setStatusData(normalizeOrderStatusPayload(order, null));
    }
  }

  async function loadBreakdown() {
    try {
      setBreakdown(await api.bookingPaymentBreakdown(order.id));
    } catch {
      setBreakdown(null);
    }
  }

  useEffect(() => {
    let closed = false;
    loadStatus();
    loadBreakdown();
    let socket;
    try {
      socket = new WebSocket(trackerSocketUrl(order.id));
      socket.onmessage = (event) => {
        if (closed) return;
        const payload = JSON.parse(event.data);
        const nextStatus = normalizeOrderStatusPayload(order, payload);
        setStatusData(nextStatus);
        if (nextStatus.paymentIntent) setPaymentIntent(nextStatus.paymentIntent);
      };
    } catch {}
    const timer = setInterval(loadStatus, 15000);
    return () => {
      closed = true;
      clearInterval(timer);
      if (socket) socket.close();
    };
  }, [order.id]);

  async function pay() {
    setBusy(true);
    setMessage("");
    try {
      const currentBreakdown = breakdown || await api.bookingPaymentBreakdown(order.id);
      setBreakdown(currentBreakdown);
      const res = await api.payBooking(order.id, { method: "razorpay" });
      const nextIntent = res.paymentIntent || res.payment_intent || null;
      if (nextIntent) setPaymentIntent(nextIntent);
      const checkoutOptions = res.razorpayCheckout || res.checkout;
      const gatewayOrderId = checkoutOptions?.razorpayOrderId || checkoutOptions?.razorpay_order_id;
      if (!gatewayOrderId) throw new Error("Razorpay checkout was not created. Please try again.");
      const paymentResult = await openRazorpayCheckout(checkoutOptions);
      const verified = await api.verifyRazorpayBookingPayment(order.id, {
        razorpay_order_id: paymentResult.razorpay_order_id,
        razorpay_payment_id: paymentResult.razorpay_payment_id,
        razorpay_signature: paymentResult.razorpay_signature,
      });
      const verifiedIntent = verified.paymentIntent || verified.payment_intent || nextIntent;
      if (verifiedIntent) setPaymentIntent(verifiedIntent);
      setMessage(verified.message || "Payment completed securely through Razorpay. Delivery OTP is now enabled.");
      if (res.breakdown) setBreakdown(res.breakdown);
      await loadStatus();
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function raiseDispute(payload) {
    setBusy(true);
    setMessage("");
    try {
      const res = await api.raiseDispute(order.id, payload);
      setMessage(res.message || "Your dispute has been raised. Our team will review it.");
      await loadStatus();
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitFeedback(payload) {
    setBusy(true);
    setMessage("");
    try {
      await api.reviewOrder(order.id, payload);
      setStatusData((old) => ({ ...old, rated: true }));
      setMessage("Feedback submitted. This review is now visible on the tailor profile.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function updateCustomerOrder(payload) {
    setBusy(true);
    setMessage("");
    try {
      const res = await api.updateCustomerBooking(order.id, payload);
      const nextBooking = res.booking || statusData;
      setStatusData((old) => normalizeOrderStatusPayload({ ...old, ...nextBooking }, { booking: nextBooking, steps: old.steps }));
      setMessage(res.message || "Order details updated before measurement.");
      await loadStatus();
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function cancelCustomerOrder(payload) {
    setBusy(true);
    setMessage("");
    try {
      const res = await api.cancelCustomerBooking(order.id, payload);
      const nextBooking = res.booking || statusData;
      setStatusData((old) => normalizeOrderStatusPayload({ ...old, ...nextBooking }, { booking: nextBooking, steps: old.steps }));
      setActiveView("");
      setMessage(res.message || "Order cancelled before measurement.");
      await loadStatus();
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  const isPaid = String(statusData.paymentStatus || statusData.payment_status || "").toLowerCase() === "paid";
  const completed = isClosedOrder(statusData);
  const cancelled = isCancelledCustomerOrder(statusData);
  const manageable = isCustomerManageAllowed(statusData);
  const currentStep = (statusData.steps || []).find((step) => step.current) || [...(statusData.steps || [])].reverse().find((step) => step.completed) || { stage: statusData.trackerStage || "Order Placed" };
  const completedCount = (statusData.steps || []).filter((step) => step.completed || step.current).length;
  const progress = statusData.steps?.length ? Math.round((completedCount / statusData.steps.length) * 100) : 14;
  const appointmentDate = statusData.appointmentDate || statusData.appointment_date;
  const deliveryDate = statusData.expectedCompletion || statusData.expected_completion;
  const blockedReason = statusData.customerManageBlockedReason || statusData.customer_manage_blocked_reason || "Manage options close on the measurement appointment date.";

  return (
    <article className={`${completed ? "compact-order-card completed" : cancelled ? "compact-order-card cancelled" : "compact-order-card"}${detailsOpen ? " details-open" : ""}`}>
      <div className="compact-order-summary">
        <div className="compact-order-id">
          <strong>{statusData.code || order.code}</strong>
          <StatusPill value={statusData.status} />
          <StatusPill value={statusData.paymentStatus || statusData.payment_status} />
        </div>
        <div>
          <h3>{statusData.serviceName || order.service_name}</h3>
          <p>{statusData.tailorName || order.shop}</p>
        </div>
        <div className="compact-progress-row" aria-label={`Order progress ${progress}%`}>
          <span><i style={{ width: `${progress}%` }} /></span>
          <b>{currentStep.stage}</b>
        </div>
        <div className="compact-order-meta">
          <span><small>Measurement</small><b>{fmtDay(appointmentDate)}</b></span>
          <span><small>Delivery</small><b>{fmtDay(deliveryDate)}</b></span>
          <span><small>Total</small><b>{money(statusData.total || order.total)}</b></span>
        </div>
      </div>

      <div className="compact-order-actions" role="tablist" aria-label={`Actions for ${statusData.code || order.code}`}>
        <button
          type="button"
          className="view-more-order-btn"
          onClick={() => {
            setDetailsOpen((open) => {
              if (open) setActiveView("");
              return !open;
            });
          }}
        >
          {detailsOpen ? "Show less" : "View more"}
        </button>
        {detailsOpen ? (
          <button type="button" className={activeView === "track" ? "active" : ""} onClick={() => setActiveView((view) => view === "track" ? "" : "track")}>
            Track order
          </button>
        ) : null}
        {detailsOpen && !completed && !cancelled ? (
          <>
            <button type="button" className={activeView === "manage" ? "active" : ""} onClick={() => setActiveView((view) => view === "manage" ? "" : "manage")} disabled={!manageable}>
              Manage order
            </button>
            <button type="button" className={activeView === "instructions" ? "active" : ""} onClick={() => setActiveView((view) => view === "instructions" ? "" : "instructions")} disabled={!manageable}>
              Update instructions
            </button>
          </>
        ) : null}
        {!isPaid && !completed && !cancelled ? <button type="button" onClick={pay} disabled={busy}>{busy ? "Opening..." : "Pay securely"}</button> : null}
        {detailsOpen && completed ? <button type="button" className={activeView === "feedback" ? "active" : ""} onClick={() => setActiveView((view) => view === "feedback" ? "" : "feedback")}>Feedback</button> : null}
      </div>

      {detailsOpen && !manageable && !completed && !cancelled ? <small className="manage-cutoff-note">{blockedReason}</small> : null}
      {cancelled ? <div className="notice">Order cancelled: {statusData.cancelReason || statusData.cancel_reason || "Cancelled before measurement."}</div> : null}

      {detailsOpen && activeView === "track" ? (
        <div className="compact-order-panel">
          <OrderTracker steps={statusData.steps} />
          {!isPaid && !cancelled ? <PaymentBreakdownCard breakdown={breakdown} /> : null}
          {!isPaid && paymentIntent && !cancelled ? <PaymentIntentNotice intent={paymentIntent} /> : null}
          {completed ? <QualityCheckPrompt onDispute={raiseDispute} busy={busy} /> : null}
        </div>
      ) : null}

      {detailsOpen && activeView === "manage" && !completed && !cancelled ? (
        <CustomerOrderManagePanel
          order={statusData}
          busy={busy}
          mode="manage"
          onUpdate={updateCustomerOrder}
          onCancel={cancelCustomerOrder}
        />
      ) : null}

      {detailsOpen && activeView === "instructions" && !completed && !cancelled ? (
        <CustomerOrderManagePanel
          order={statusData}
          busy={busy}
          mode="instructions"
          onUpdate={updateCustomerOrder}
          onCancel={cancelCustomerOrder}
        />
      ) : null}

      {detailsOpen && activeView === "feedback" && completed ? <OrderFeedbackCard order={statusData} onSubmit={submitFeedback} busy={busy} /> : null}
      {message ? <div className={message.includes("raised") || message.includes("completed") || message.includes("submitted") || message.includes("created") || message.includes("verified") || message.includes("securely") || message.includes("updated") || message.includes("cancelled") ? "notice ok" : "error"}>{message}</div> : null}
    </article>
  );
}

function CustomerOrderManagePanel({ order, busy, mode, onUpdate, onCancel }) {
  const [deliveryDate, setDeliveryDate] = useState(orderDateInput(order.expectedCompletion || order.expected_completion));
  const [instructions, setInstructions] = useState(order.notes || "");
  const [cancelReason, setCancelReason] = useState("");
  const [localError, setLocalError] = useState("");
  const appointmentDate = orderDateInput(order.appointmentDate || order.appointment_date);
  const minFromAppointment = appointmentDate ? addDaysToDateInput(appointmentDate, MEASUREMENT_APPOINTMENT_BLOCKED_WINDOW_DAYS + 1) : "";
  const minDeliveryDate = laterDateInput(todayDateInput(), minFromAppointment);

  useEffect(() => {
    setDeliveryDate(orderDateInput(order.expectedCompletion || order.expected_completion));
    setInstructions(order.notes || "");
    setCancelReason("");
    setLocalError("");
  }, [order.id, order.expectedCompletion, order.expected_completion, order.notes]);

  async function submitDelivery(event) {
    event.preventDefault();
    setLocalError("");
    if (!deliveryDate) {
      setLocalError("Choose the new delivery date.");
      return;
    }
    if (minDeliveryDate && deliveryDate < minDeliveryDate) {
      setLocalError("Delivery date must be at least 3 days after the measurement appointment.");
      return;
    }
    await onUpdate({ preferredDate: deliveryDate });
  }

  async function submitInstructions(event) {
    event.preventDefault();
    setLocalError("");
    if (!instructions.trim()) {
      setLocalError("Write the updated stitching instructions.");
      return;
    }
    await onUpdate({ instructions: instructions.trim() });
  }

  async function submitCancel(event) {
    event.preventDefault();
    setLocalError("");
    const reason = cancelReason.trim();
    if (reason.length < 5) {
      setLocalError("Add a clear cancellation reason.");
      return;
    }
    await onCancel({ reason });
  }

  if (!isCustomerManageAllowed(order)) {
    return <div className="compact-order-panel"><div className="notice">{order.customerManageBlockedReason || "Manage options are available only before the measurement appointment date."}</div></div>;
  }

  if (mode === "instructions") {
    return (
      <form className="compact-order-panel order-manage-grid single" onSubmit={submitInstructions}>
        <label>
          Updated stitching instructions
          <textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} placeholder="Example: Keep sleeve length 10 inches and add extra margin." />
        </label>
        {localError ? <small className="field-error">{localError}</small> : null}
        <button type="submit" className="primary-btn compact-action" disabled={busy}>{busy ? "Saving..." : "Save instructions"}</button>
      </form>
    );
  }

  return (
    <div className="compact-order-panel order-manage-grid">
      <form onSubmit={submitDelivery}>
        <h3>Modify delivery date</h3>
        <p>Allowed only before the measurement appointment date.</p>
        <label>
          New delivery date
          <input type="date" value={deliveryDate} min={minDeliveryDate || undefined} onChange={(event) => setDeliveryDate(event.target.value)} />
        </label>
        <button type="submit" className="secondary-btn" disabled={busy}>{busy ? "Saving..." : "Update delivery date"}</button>
      </form>
      <form onSubmit={submitCancel}>
        <h3>Cancel order</h3>
        <p>Cancellation closes automatically once the measurement date starts.</p>
        <label>
          Cancellation reason
          <textarea value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} placeholder="Example: Need to change fabric and will book again later." />
        </label>
        <button type="submit" className="danger-btn" disabled={busy}>{busy ? "Cancelling..." : "Cancel order"}</button>
      </form>
      {localError ? <small className="field-error span-2">{localError}</small> : null}
    </div>
  );
}

function PaymentIntentNotice({ intent }) {
  const status = String(intent.status || "").replaceAll("_", " ");
  const reference = intent.paymentReference || intent.payment_reference;
  const gatewayOrderId = intent.gatewayOrderId || intent.gateway_order_id;
  const expiresIn = Number(intent.expiresInSeconds ?? intent.expires_in_seconds ?? 0);
  const expiresText = expiresIn > 0 ? `${Math.ceil(expiresIn / 60)} min left` : "expired";
  return (
    <div className={String(intent.status).toLowerCase() === "pending" ? "notice payment-intent-notice" : "notice"}>
      <strong>Razorpay payment reference: {reference}</strong>
      <span>Status: {status || "pending"} - {expiresText}</span>
      {gatewayOrderId ? <small>Gateway order: {gatewayOrderId}</small> : null}
      <small>Tailor wallet credit happens only after Razorpay signature verification succeeds.</small>
    </div>
  );
}

function PaymentBreakdownCard({ breakdown }) {
  if (!breakdown) {
    return <div className="payment-breakdown"><small>Loading payment breakdown...</small></div>;
  }
  const orderAmount = breakdown.orderAmount ?? breakdown.order_amount;
  const serviceAmount = breakdown.serviceAmount ?? breakdown.service_amount ?? orderAmount;
  const travelChargeAmount = breakdown.travelChargeAmount ?? breakdown.travel_charge_amount ?? 0;
  const travelRate = breakdown.travelRatePerKm ?? breakdown.travel_rate_per_km ?? TRAVEL_CHARGE_PER_KM;
  const gstAmount = breakdown.gstAmount ?? breakdown.gst_amount;
  const gstPercentage = breakdown.gstPercentage ?? breakdown.gst_percentage;
  const platformFeeAmount = breakdown.platformFeeAmount ?? breakdown.platform_fee_amount;
  const platformFeePercentage = breakdown.platformFeePercentage ?? breakdown.platform_fee_percentage;
  const payableTotal = breakdown.payableTotal ?? breakdown.payable_total;
  return (
    <div className="payment-breakdown">
      <div><span>Service amount</span><strong>{money(serviceAmount)}</strong></div>
      <div><span>Home visit travel ({money(travelRate)}/km)</span><strong>{Number(travelChargeAmount || 0) > 0 ? money(travelChargeAmount) : "Not applicable"}</strong></div>
      <div><span>Order subtotal</span><strong>{money(orderAmount)}</strong></div>
      <div><span>GST {Number(gstPercentage || 0)}%</span><strong>{money(gstAmount)}</strong></div>
      <div><span>Platform fee {Number(platformFeePercentage || 0)}%</span><strong>{money(platformFeeAmount)}</strong></div>
      <div className="total"><span>Total to pay</span><strong>{money(payableTotal)}</strong></div>
    </div>
  );
}

function OrderTracker({ steps = [] }) {
  const rows = steps.length ? steps : bookingTrackerStages.map((stage, index) => ({ stage, completed: index === 0, current: index === 0 }));
  const currentStep = rows.find((step) => step.current) || [...rows].reverse().find((step) => step.completed) || rows[0];
  const completedCount = rows.filter((step) => step.completed || step.current).length;
  const progress = rows.length ? Math.round((completedCount / rows.length) * 100) : 0;
  return (
    <div className="tracker-panel">
      <div className="tracker-panel-head">
        <div>
          <span className="tracker-label">Order progress</span>
          <strong>{currentStep?.stage || "Order Placed"}</strong>
          <small>{currentStep?.timestamp ? fmtDate(currentStep.timestamp) : "Live tracker updates as the tailor moves each stage."}</small>
        </div>
        <div className="tracker-progress">
          <b>{progress}%</b>
          <span><i style={{ width: `${progress}%` }} /></span>
        </div>
      </div>
      <div className="order-stepper luxury-tracker">
        {rows.map((step, index) => (
          <div key={step.stage} className={step.current ? "order-step current" : step.completed ? "order-step done" : "order-step"} aria-current={step.current ? "step" : undefined}>
            <span className="tracker-node">
              {step.completed ? <CheckCircle2 size={16} /> : step.current ? <i className="live-dot" /> : index + 1}
            </span>
            <div>
              <strong>{step.stage}</strong>
              <small>{step.timestamp ? fmtDate(step.timestamp) : step.completed ? "Completed" : step.current ? "In progress" : "Pending"}</small>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function QualityCheckPrompt({ onDispute, busy }) {
  const [reason, setReason] = useState("");
  const [file, setFile] = useState(null);
  const [localError, setLocalError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setLocalError("");
    const cleanReason = reason.trim();
    if (cleanReason.length < 5) {
      setLocalError("Add a clear dispute reason.");
      return;
    }
    const payload = { reason: cleanReason };
    if (file) {
      if (!file.type.startsWith("image/")) {
        setLocalError("Upload a stitched item photo.");
        return;
      }
      if (file.size > 8 * 1024 * 1024) {
        setLocalError("Photo must be 8 MB or smaller.");
        return;
      }
      payload.photoName = file.name;
      payload.photoMediaType = file.type;
      payload.photoUrl = await readFileAsDataUrl(file);
    }
    await onDispute(payload);
    setReason("");
    setFile(null);
    event.target.reset();
  }

  return (
    <form className="quality-check-card" onSubmit={submit}>
      <div>
        <h3>Check your stitched item</h3>
        <p>Review fitting, measurements, finishing, fabric condition and delivered pieces before closing your handover check.</p>
      </div>
      <label>
        Dispute reason
        <textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Describe the issue with fitting, stitching, item condition or delivery" />
      </label>
      <label className="upload-action">
        <UploadCloud size={16} />
        <span>{file ? file.name : "Upload stitched item photo"}</span>
        <input type="file" accept="image/*" onChange={(event) => setFile(event.target.files?.[0] || null)} disabled={busy} />
      </label>
      {localError ? <small className="field-error">{localError}</small> : null}
      <button type="submit" className="secondary-btn" disabled={busy}>Do you have a dispute? Raise a ticket.</button>
    </form>
  );
}

function OrderFeedbackCard({ order, onSubmit, busy }) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [body, setBody] = useState("");
  const [localError, setLocalError] = useState("");
  const alreadyReviewed = Boolean(order.rated);

  async function submit(event) {
    event.preventDefault();
    setLocalError("");
    if (!rating) {
      setLocalError("Please select a star rating before submitting feedback.");
      return;
    }
    await onSubmit({ rating, body: body.trim() || null, images: [] });
    setBody("");
    setRating(0);
    setHoverRating(0);
  }

  if (alreadyReviewed) {
    return (
      <div className="order-feedback-card submitted">
        <div>
          <span>Order feedback</span>
          <h3>Feedback submitted</h3>
          <p>Your rating is now visible on this tailor's public profile.</p>
        </div>
        <span className="pill ok">Reviewed</span>
      </div>
    );
  }

  return (
    <form className="order-feedback-card" onSubmit={submit}>
      <div className="feedback-copy">
        <span>Optional feedback</span>
        <h3>Rate this order</h3>
        <p>Share how the fitting, finishing, delivery and service felt for this completed order.</p>
      </div>
      <div className="star-rating-input" role="radiogroup" aria-label="Order rating">
        {[1, 2, 3, 4, 5].map((value) => {
          const active = value <= (hoverRating || rating);
          return (
            <button
              type="button"
              key={value}
              className={active ? "active" : ""}
              onClick={() => setRating(value)}
              onMouseEnter={() => setHoverRating(value)}
              onMouseLeave={() => setHoverRating(0)}
              aria-label={`${value} star${value === 1 ? "" : "s"}`}
              aria-checked={rating === value}
              role="radio"
            >
              <Star size={22} />
            </button>
          );
        })}
        <strong>{rating ? `${rating}.0` : "Select rating"}</strong>
      </div>
      <label>
        Comment (optional)
        <textarea value={body} onChange={(event) => setBody(event.target.value)} placeholder="Example: Perfect blouse fitting and delivery was on time." />
      </label>
      {localError ? <small className="field-error">{localError}</small> : null}
      <button type="submit" className="primary-btn" disabled={busy}>{busy ? "Submitting..." : "Submit Feedback"}</button>
    </form>
  );
}

function SupportPanel({ role, orders = [] }) {
  const isCustomer = role === "customer";
  const categories = useMemo(
    () => [...new Set([...(isCustomer ? customerSupportCategories : tailorSupportCategories), "Account deletion request"])],
    [isCustomer],
  );
  const [tickets, setTickets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ category: categories[0], priority: "NORMAL", subject: "", description: "", orderId: "" });
  const [reply, setReply] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadTickets(nextSelectedId) {
    const list = isCustomer ? await api.customerSupportTickets() : await api.tailorSupportTickets();
    setTickets(list);
    const selectedId = nextSelectedId || selected?.id || list[0]?.id;
    if (selectedId) {
      const detail = isCustomer ? await api.customerSupportTicket(selectedId) : await api.tailorSupportTicket(selectedId);
      setSelected(detail);
    } else {
      setSelected(null);
    }
  }

  useEffect(() => {
    loadTickets().catch((err) => setMessage(err.message));
  }, [role]);

  function update(key, value) {
    setForm((old) => ({ ...old, [key]: value }));
  }

  function prepareDeletionRequest() {
    setForm((old) => ({
      ...old,
      category: "Account deletion request",
      priority: "HIGH",
      orderId: "",
      subject: "Request to delete my TailoraHub account",
      description: "I want to delete my TailoraHub account. Please verify my identity and process account deletion.",
    }));
  }

  async function createTicket(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const payload = { ...form, orderId: form.orderId || null };
      const created = isCustomer ? await api.createCustomerSupportTicket(payload) : await api.createTailorSupportTicket(payload);
      setForm({ category: categories[0], priority: "NORMAL", subject: "", description: "", orderId: "" });
      setMessage(`Ticket ${created.code} created.`);
      await loadTickets(created.id);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function openTicket(ticket) {
    setBusy(true);
    setMessage("");
    try {
      const detail = isCustomer ? await api.customerSupportTicket(ticket.id) : await api.tailorSupportTicket(ticket.id);
      setSelected(detail);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendReply(event) {
    event.preventDefault();
    if (!selected || !reply.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const detail = isCustomer ? await api.replyCustomerSupportTicket(selected.id, reply) : await api.replyTailorSupportTicket(selected.id, reply);
      setReply("");
      setSelected(detail);
      await loadTickets(detail.id);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function closeTicket() {
    if (!selected || !confirm("Close this support ticket?")) return;
    setBusy(true);
    setMessage("");
    try {
      const detail = isCustomer ? await api.closeCustomerSupportTicket(selected.id) : await api.closeTailorSupportTicket(selected.id);
      setSelected(detail);
      await loadTickets(detail.id);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="section-block no-top support-panel">
      <div className="support-grid">
        <form className="support-create" onSubmit={createTicket}>
          <h3>{isCustomer ? "Customer Support" : "Tailor Support"}</h3>
          <label>Category<select value={form.category} onChange={(e) => update("category", e.target.value)}>{categories.map((c) => <option key={c} value={c}>{c}</option>)}</select></label>
          <label>Priority<select value={form.priority} onChange={(e) => update("priority", e.target.value)}>{supportPriorities.map((p) => <option key={p} value={p}>{p.replaceAll("_", " ")}</option>)}</select></label>
          <label>Related order<select value={form.orderId} onChange={(e) => update("orderId", e.target.value)}><option value="">No related order</option>{orders.map((o) => <option key={o.id} value={o.id}>{o.code} - {o.service_name}</option>)}</select></label>
          <label>Subject<input value={form.subject} onChange={(e) => update("subject", e.target.value)} placeholder="Short issue summary" /></label>
          <label>Description<textarea value={form.description} onChange={(e) => update("description", e.target.value)} placeholder="Explain what happened and what help you need" /></label>
          <div className="inline-actions support-form-actions">
            <button type="button" className="secondary-btn support-delete-request" onClick={prepareDeletionRequest} disabled={busy}>Request account deletion</button>
            <button className="primary-btn" disabled={busy}>Create Ticket</button>
          </div>
        </form>
        <div className="support-list">
          <div className="section-head">
            <h3>My Tickets</h3>
            <button className="secondary-btn" onClick={() => loadTickets()} disabled={busy}>Refresh</button>
          </div>
          {message ? <div className={message.includes("created") ? "notice ok" : "error"}>{message}</div> : null}
          <PaginatedCards
            items={tickets}
            pageSize={5}
            className="support-ticket-list"
            label="tickets"
            emptyText="No support tickets yet."
            renderItem={(ticket) => (
              <button className={selected?.id === ticket.id ? "support-ticket active" : "support-ticket"} onClick={() => openTicket(ticket)}>
                <strong>{ticket.code}</strong>
                <span>{ticket.subject}</span>
                <small>{ticket.category} - {ticket.message_count || ticket.messages?.length || 0} messages</small>
                <div className="inline-actions"><StatusPill value={ticket.priority} /><StatusPill value={ticket.status} /></div>
              </button>
            )}
          />
        </div>
      </div>
      {selected ? (
        <div className="support-detail">
          <div className="section-head">
            <div>
              <h3>{selected.code} - {selected.subject}</h3>
              <p>{selected.category}{selected.order_code ? ` - ${selected.order_code}` : ""}</p>
            </div>
            <div className="inline-actions"><StatusPill value={selected.priority} /><StatusPill value={selected.status} /></div>
          </div>
          <ViewMoreGrid
            items={selected.messages || []}
            initial={6}
            step={6}
            className="support-thread"
            label="messages"
            emptyText="No messages yet."
            renderItem={(row) => (
              <div className={`support-message ${row.author_role === "admin" ? "agent" : "requester"}`}>
                <strong>{row.author_name} <span>{row.author_role}</span></strong>
                <p>{row.body}</p>
                <small>{fmtDate(row.created_at)}</small>
              </div>
            )}
          />
          {selected.status !== "CLOSED" ? (
            <form className="support-reply" onSubmit={sendReply}>
              <label>Reply<textarea value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Add more details or respond to support" /></label>
              <div className="inline-actions">
                <button className="primary-btn" disabled={busy}>Send Reply</button>
                <button type="button" className="secondary-btn" onClick={closeTicket} disabled={busy}>Close Ticket</button>
              </div>
            </form>
          ) : <div className="notice ok">This support ticket is closed.</div>}
        </div>
      ) : null}
    </section>
  );
}

function TailorApp({ onLogout }) {
  const t = useT();
  const [data, setData] = useState(null);
  const [availability, setAvailability] = useState({});
  const [activePanel, setActivePanel] = useAppHistoryState("tailorPanel", "overview");
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const next = await api.tailorDashboard();
      setData(next);
      setAvailability({
        availability: next.tailor.availability || "AVAILABLE",
        availableSlots: next.tailor.availableSlots || 0,
        maxNewOrders: next.tailor.maxNewOrders || 0,
        nextAvailable: next.tailor.nextAvailable || "",
        availabilityNote: next.tailor.availabilityNote || "",
        acceptingRequests: next.tailor.acceptingRequests,
      });
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, []);

  async function saveAvailability(event) {
    event.preventDefault();
    await api.updateAvailability({ ...availability, nextAvailable: availability.nextAvailable || null });
    load();
  }

  const unreadUpdates = unreadCount(data?.notifications || []);

  useEffect(() => {
    if (!data || activePanel !== "updates" || !unreadUpdates) return;
    let cancelled = false;
    api.markTailorNotificationsRead()
      .then(() => {
        if (cancelled) return;
        setData((old) => old ? {
          ...old,
          notifications: (old.notifications || []).map((row) => ({ ...row, read: true })),
        } : old);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [data, activePanel, unreadUpdates]);

  if (!data) return <Shell title={t("dashboard.tailor.title", "Tailor Dashboard")} subtitle={t("dashboard.tailor.subtitle", "Requests, orders and availability")} icon={Scissors} onLogout={onLogout}>{error ? <div className="error banner">{error}</div> : <div className="loading">{t("tailor.loading", "Loading tailor dashboard...")}</div>}</Shell>;
  const pendingApproval = data.tailor.approvalStatus !== "APPROVED";
  const mediaCount = portfolioItems(data.tailor.portfolio).length;
  const activeOffers = (data.offers || []).filter((offer) => offer.active !== false).length;
  const panels = [
    ["overview", t("common.overview", "Overview"), LayoutDashboard, null],
    ["availability", t("common.availability", "Availability"), CheckCircle2, null],
    ["wallet", t("common.wallet", "Wallet"), CreditCard, null],
    ["referrals", t("common.referrals", "Referrals"), UsersRound, null],
    ["media", t("common.photosVideos", "Photos / Videos"), ImageIcon, null],
    ["services", t("common.services", "Services"), Tag, null],
    ["offers", t("common.offers", "Offers"), Megaphone, null],
    ["followers", t("common.followers", "Followers"), UsersRound, null],
    ["requests", t("common.requests", "Requests"), ClipboardList, null],
    ["waiting", t("common.waitingList", "Waiting List"), FileClock, null],
    ["orders", t("common.orders", "Orders"), Scissors, null],
    ["updates", t("common.updates", "Updates"), FileClock, unreadUpdates],
    ["support", t("common.support", "Support"), AlertTriangle, null],
  ];

  return (
    <Shell title={t("dashboard.tailor.title", "Tailor Dashboard")} subtitle={data.tailor.shop} icon={Scissors} onLogout={onLogout} actions={<button className="icon-btn" onClick={load} title={t("common.refresh", "Refresh")}><RefreshCw size={17} /></button>}>
      {error ? <div className="error banner">{error}</div> : null}
      {pendingApproval ? <div className="notice warn">{t("tailor.profilePending", `Your tailor profile is ${data.tailor.approvalStatus}. Customers will see you only after admin approval.`, { status: data.tailor.approvalStatus })}</div> : null}
      <div className="tailor-workspace">
        <aside className="tailor-side-card">
          <div className="tailor-side-head">
            <TailorAvatar tailor={data.tailor} />
            <div>
              <h3>{data.tailor.shop}</h3>
              <p>{data.tailor.ownerName}</p>
            </div>
          </div>
          <StatusPill value={data.tailor.availability} />
          <small>{data.tailor.availabilityNote || t(`availability.${data.tailor.availability}`, availabilityCopy[data.tailor.availability])}</small>
          <nav className="tailor-side-nav">
            {panels.map(([id, label, Icon, count]) => (
              <button key={id} className={activePanel === id ? "active" : ""} onClick={() => setActivePanel(id)}>
                <Icon size={16} />
                <span>{label}</span>
                {count ? <b>{count}</b> : null}
              </button>
            ))}
          </nav>
        </aside>
        <div className="tailor-content">
          {activePanel === "overview" ? (
            <>
              <div className="kpi-grid">
                <Kpi label={t("tailor.pendingRequests", "Pending Requests")} value={data.stats.pending_requests} icon={ClipboardList} />
                <Kpi label={t("tailor.activeOrders", "Active Orders")} value={data.stats.active_orders} icon={Scissors} />
                <Kpi label={t("tailor.completedOrders", "Completed Orders")} value={data.stats.completed_orders} icon={CheckCircle2} />
                <Kpi label={t("tailor.earnings", "Earnings")} value={money(data.stats.earnings)} icon={CreditCard} />
                <Kpi label={t("common.followers", "Followers")} value={data.stats.followers || 0} icon={UsersRound} />
                <Kpi label={t("common.favorites", "Favorites")} value={data.stats.favorites || 0} icon={Heart} />
              </div>
              <div className="two-col overview-cards">
                <div className="record-card">
                  <h3>{t("tailor.currentAvailability", "Current Availability")}</h3>
                  <StatusPill value={data.tailor.availability} />
                  <p>{data.tailor.availabilityNote || t(`availability.${data.tailor.availability}`, availabilityCopy[data.tailor.availability])}</p>
                  <small>{t("tailor.availableSlots", "Available slots")}: {data.tailor.availableSlots || 0}</small>
                  <small>{t("tailor.nextAvailable", "Next available")}: {fmtDay(data.tailor.nextAvailable)}</small>
                </div>
                <div className="record-card">
                  <h3>{t("tailor.publicMedia", "Public Media")}</h3>
                  <p>{mediaCount ? `${mediaCount} photo/video item${mediaCount === 1 ? "" : "s"} visible to customers.` : "No photo or video uploaded yet."}</p>
                  <button className="secondary-btn" onClick={() => setActivePanel("media")}>{t("tailor.manageMedia", "Manage Media")}</button>
                </div>
                <div className="record-card">
                  <h3>{t("tailor.followerUpdates", "Follower Updates")}</h3>
                  <p>{data.stats.followers ? `${data.stats.followers} customer profile${data.stats.followers === 1 ? "" : "s"} will get in-app updates when you post media or offers.` : t("tailor.noFollowers", "No followers yet.")}</p>
                  <button className="secondary-btn" onClick={() => setActivePanel("offers")}>{t("tailor.postOffer", "Post Offer")}</button>
                </div>
              </div>
            </>
          ) : null}
          {activePanel === "availability" ? <TailorAvailabilityPanel availability={availability} setAvailability={setAvailability} saveAvailability={saveAvailability} /> : null}
          {activePanel === "wallet" ? <TailorWalletPanel /> : null}
          {activePanel === "referrals" ? <TailorReferralPanel /> : null}
          {activePanel === "media" ? <TailorMediaPanel tailor={data.tailor} reload={load} /> : null}
          {activePanel === "services" ? <TailorServicesPanel /> : null}
          {activePanel === "offers" ? <TailorOffersPanel offers={data.offers || []} reload={load} /> : null}
          {activePanel === "followers" ? <TailorFollowersPanel followers={data.followers || []} /> : null}
          {activePanel === "requests" ? <TailorRequests rows={data.requests} reload={load} /> : null}
          {activePanel === "waiting" ? <TailorWaitingListPanel reloadDashboard={load} /> : null}
          {activePanel === "orders" ? <TailorOrders rows={data.orders} reload={load} /> : null}
          {activePanel === "updates" ? <Updates title={t("tailor.updatesTitle", "Tailor Updates")} rows={data.notifications || []} /> : null}
          {activePanel === "support" ? <SupportPanel role="tailor" orders={data.orders || []} /> : null}
        </div>
      </div>
    </Shell>
  );
}

function TailorAvailabilityPanel({ availability, setAvailability, saveAvailability }) {
  const t = useT();
  return (
    <section className="section-block no-top">
      <h3>{t("common.availability", "Availability")}</h3>
      <form className="availability-form" onSubmit={saveAvailability}>
        <label>{t("tailor.status", "Status")}<select value={availability.availability} onChange={(e) => setAvailability({ ...availability, availability: e.target.value })}><option value="AVAILABLE">{t("common.available", "Available")}</option><option value="FEW_SLOTS_AVAILABLE">{t("common.fewSlots", "Few Slots Available")}</option><option value="BUSY">{t("common.busy", "Busy")}</option><option value="NOT_AVAILABLE">{t("common.unavailable", "Not Available")}</option></select></label>
        <label>{t("tailor.availableSlots", "Available slots")}<input type="number" min="0" value={availability.availableSlots} onChange={(e) => setAvailability({ ...availability, availableSlots: Number(e.target.value) })} /></label>
        <label>{t("tailor.maxNewOrders", "Max new orders")}<input type="number" min="0" value={availability.maxNewOrders} onChange={(e) => setAvailability({ ...availability, maxNewOrders: Number(e.target.value) })} /></label>
        <label>{t("tailor.nextAvailableDate", "Next available date")}<input type="date" value={availability.nextAvailable || ""} onChange={(e) => setAvailability({ ...availability, nextAvailable: e.target.value })} /></label>
        <label className="check-row"><input type="checkbox" checked={Boolean(availability.acceptingRequests)} onChange={(e) => setAvailability({ ...availability, acceptingRequests: e.target.checked })} /> {t("tailor.acceptingRequests", "Accepting new requests")}</label>
        <label className="span-2">{t("tailor.availabilityNote", "Availability note")}<textarea value={availability.availabilityNote} onChange={(e) => setAvailability({ ...availability, availabilityNote: e.target.value })} /></label>
        <button className="primary-btn">{t("tailor.saveAvailability", "Save Availability")}</button>
      </form>
    </section>
  );
}

function TailorWalletPanel() {
  const t = useT();
  const [wallet, setWallet] = useState(null);
  const [upiId, setUpiId] = useState("");
  const [withdraw, setWithdraw] = useState({ amount: "", destinationType: "upi_id", otp: "", bankAccountNumber: "", bankIfsc: "" });
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [otpSent, setOtpSent] = useState(false);
  const [otpTarget, setOtpTarget] = useState("");

  async function load() {
    setLoading(true);
    setMessage("");
    try {
      const nextWallet = await api.walletMe();
      setWallet(nextWallet);
      setUpiId(nextWallet.upi_id || "");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function saveUpi(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const nextWallet = await api.setWalletUpi(upiId);
      setWallet(nextWallet);
      setMessage("UPI ID updated for your wallet.");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendOtp() {
    setBusy(true);
    setMessage("");
    try {
      const res = await api.sendWithdrawOtp();
      setOtpSent(true);
      setOtpTarget(res.target || "");
      setMessage(res.dev_otp || res.devOtp ? `Dev mode withdrawal OTP: ${res.dev_otp || res.devOtp}` : `Withdrawal OTP sent to ${res.target || "registered contact"}.`);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitWithdraw(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const payload = {
        amount: Number(withdraw.amount || 0),
        destination_type: withdraw.destinationType,
        otp: withdraw.otp,
      };
      if (withdraw.destinationType === "bank_account") {
        payload.bank_account_number = withdraw.bankAccountNumber;
        payload.bank_ifsc = withdraw.bankIfsc;
      }
      const res = await api.withdrawWallet(payload);
      setWallet((old) => ({ ...old, balance: res.balance ?? old?.balance }));
      setWithdraw({ amount: "", destinationType: "upi_id", otp: "", bankAccountNumber: "", bankIfsc: "" });
      setOtpSent(false);
      setOtpTarget("");
      const successMessage = res.message || `Withdrawal request ${res.status}. Reference: ${res.txn_ref || "not available"}. Admin will process manual payout within 24 hours.`;
      await load();
      setMessage(successMessage);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <section className="section-block no-top"><div className="loading">{t("wallet.loading", "Loading wallet...")}</div></section>;
  }

  const walletAvailableBalance = wallet?.available_balance ?? wallet?.availableBalance ?? wallet?.balance ?? 0;
  const walletLedgerBalance = wallet?.ledger_balance ?? wallet?.ledgerBalance ?? wallet?.balance ?? 0;
  const pendingWithdrawalAmount = wallet?.pending_withdrawal_amount ?? wallet?.pendingWithdrawalAmount ?? 0;

  return (
    <section className="section-block no-top">
      <div className="section-head">
        <div>
          <h3>{t("common.wallet", "Wallet")}</h3>
          <p>{t("tailor.walletDescription", "QR payments credit your wallet ledger without showing your UPI or bank details to customers.")}</p>
        </div>
        <button type="button" className="secondary-btn" onClick={load} disabled={busy}>{t("common.refresh", "Refresh")}</button>
      </div>
      {message ? <div className={message.includes("updated") || message.includes("sent") || message.includes("success") ? "notice ok" : "notice"}>{message}</div> : null}
      <div className="wallet-layout">
        <div className="wallet-card">
          <div>
            <small>Net available after commission</small>
            <strong>{money(walletAvailableBalance)}</strong>
            <span>Wallet ID {String(wallet?.wallet_id || "").slice(0, 8)}...</span>
            <small>Ledger {money(walletLedgerBalance)} - Pending withdrawal {money(pendingWithdrawalAmount)}</small>
          </div>
          <div className="wallet-qr-tile">
            {wallet?.qr_code_url ? <img src={assetUrl(wallet.qr_code_url)} alt="Wallet payment QR" /> : <span>No QR yet</span>}
          </div>
        </div>
        <form className="record-card stack-form" onSubmit={saveUpi}>
          <h3>UPI ID</h3>
          <p>{t("tailor.upiVisible", "Visible only to you and authorized admins. Customers pay using the QR token.")}</p>
          <Field label="UPI ID">
            <input value={upiId} onChange={(e) => setUpiId(e.target.value)} placeholder="name@bank" />
          </Field>
          <button className="primary-btn" disabled={busy}>{busy ? "Saving..." : "Set / Update UPI ID"}</button>
        </form>
      </div>
      <form className="record-card withdraw-form" onSubmit={submitWithdraw}>
        <div className="section-head">
          <div>
            <h3>Withdraw Funds</h3>
            <p>Withdrawal requires OTP confirmation before processing.</p>
          </div>
          <button type="button" className="secondary-btn" onClick={sendOtp} disabled={busy}>{otpSent ? "Resend OTP" : "Send OTP"}</button>
        </div>
        <div className="form-grid">
          <Field label="Amount">
            <input type="number" min="1" max={Number(walletAvailableBalance || 0)} value={withdraw.amount} onChange={(e) => setWithdraw((old) => ({ ...old, amount: e.target.value }))} />
          </Field>
          <Field label="Destination">
            <select value={withdraw.destinationType} onChange={(e) => setWithdraw((old) => ({ ...old, destinationType: e.target.value }))}>
              <option value="upi_id">UPI ID</option>
              <option value="bank_account">Bank account</option>
            </select>
          </Field>
          {withdraw.destinationType === "bank_account" ? (
            <>
              <Field label="Bank account number">
                <input value={withdraw.bankAccountNumber} onChange={(e) => setWithdraw((old) => ({ ...old, bankAccountNumber: e.target.value }))} />
              </Field>
              <Field label="IFSC">
                <input value={withdraw.bankIfsc} onChange={(e) => setWithdraw((old) => ({ ...old, bankIfsc: e.target.value.toUpperCase() }))} />
              </Field>
            </>
          ) : null}
          <Field label="Withdrawal OTP" hint={otpTarget ? `Sent to ${otpTarget}` : "Send OTP before withdrawing"}>
            <input value={withdraw.otp} onChange={(e) => setWithdraw((old) => ({ ...old, otp: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} />
          </Field>
        </div>
        <button className="primary-btn" disabled={busy || !otpSent}>{busy ? "Processing..." : "Withdraw"}</button>
      </form>
    </section>
  );
}

function TailorReferralPanel() {
  const t = useT();
  const [referral, setReferral] = useState(null);
  const [count, setCount] = useState(0);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setMessage("");
    try {
      const [codeData, countData] = await Promise.all([
        api.myReferralCode(),
        api.myReferralCount(),
      ]);
      setReferral(codeData);
      setCount(countData.direct_count ?? countData.directCount ?? 0);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function copyReferral(value) {
    setMessage("");
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(value);
      setMessage("Referral link copied.");
    } catch {
      setMessage("Copy is blocked in this browser. Select the link and copy it manually.");
    }
  }

  const code = referral?.referral_code || referral?.referralCode || "";
  const link = referral?.shareable_link || referral?.shareableLink || "";

  if (loading) {
    return <section className="section-block no-top"><div className="loading">{t("referrals.loading", "Loading referrals...")}</div></section>;
  }

  return (
    <section className="section-block no-top">
      <div className="section-head">
        <div>
          <h3>{t("common.referrals", "Referrals")}</h3>
          <p>{t("tailor.referralHelp", "Share your code with other tailors. Your dashboard shows only the people you directly referred.")}</p>
        </div>
        <button type="button" className="secondary-btn" onClick={load}>{t("common.refresh", "Refresh")}</button>
      </div>
      {message ? <div className={message.includes("copied") ? "notice ok" : "notice"}>{message}</div> : null}
      <div className="referral-summary-grid">
        <div className="referral-card referral-code-card">
          <span>{t("customer.referralCode", "Your referral code")}</span>
          <strong>{code || "-"}</strong>
          <button type="button" className="secondary-btn" onClick={() => copyReferral(code)} disabled={!code}>Copy Code</button>
        </div>
        <div className="referral-card">
          <span>{t("tailor.youReferred", "You have referred")}</span>
          <strong>{count}</strong>
          <small>{count === 1 ? "Tailor joined with your code" : "Tailors joined with your code"}</small>
        </div>
      </div>
      <div className="record-card referral-share-card">
        <h3>{t("referrals.shareableLink", "Shareable Link")}</h3>
        <div className="share-link-row">
          <input readOnly value={link} aria-label="Shareable referral link" />
          <button type="button" className="primary-btn" onClick={() => copyReferral(link)} disabled={!link}>Copy Link</button>
        </div>
      </div>
    </section>
  );
}

function TailorMediaPanel({ tailor, reload }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function uploadProfileImage(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setMessage("");
    try {
      if (!file.type.startsWith("image/")) {
        throw new Error("Profile picture must be an image");
      }
      if (file.size > 5 * 1024 * 1024) {
        throw new Error("Profile picture must be 5 MB or smaller");
      }
      const dataUrl = await readFileAsDataUrl(file);
      await api.uploadTailorProfileImage({ name: file.name, mediaType: file.type, dataUrl });
      setMessage("Profile picture updated and visible to customers.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      event.target.value = "";
      setBusy(false);
    }
  }

  async function removeProfileImage() {
    if (!confirm("Remove your public profile picture?")) return;
    setBusy(true);
    setMessage("");
    try {
      await api.deleteTailorProfileImage();
      setMessage("Profile picture removed.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function upload(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setBusy(true);
    setMessage("");
    try {
      for (const file of files) {
        if (!file.type.startsWith("image/") && !file.type.startsWith("video/")) {
          throw new Error("Only photo or video files are allowed");
        }
        if (file.size > 15 * 1024 * 1024) {
          throw new Error("Each upload must be 15 MB or smaller");
        }
        const dataUrl = await readFileAsDataUrl(file);
        await api.uploadTailorMedia({ name: file.name, mediaType: file.type, dataUrl });
      }
      setMessage("Media uploaded and visible to customers.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      event.target.value = "";
      setBusy(false);
    }
  }

  async function remove(index) {
    if (!confirm("Remove this photo/video from your public profile?")) return;
    setBusy(true);
    setMessage("");
    try {
      await api.deleteTailorMedia(index);
      setMessage("Media removed.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="section-block no-top">
      <div className="profile-photo-card">
        <TailorAvatar tailor={tailor} size="xl" />
        <div>
          <h3>Profile Picture</h3>
          <p>This picture appears as your DP on customer listings and profile pages.</p>
          <div className="inline-actions">
            <label className="upload-action">
              <UploadCloud size={16} />
              <span>{busy ? "Uploading..." : "Upload DP"}</span>
              <input type="file" accept="image/*" onChange={uploadProfileImage} disabled={busy} />
            </label>
            {tailor.profileImage ? <button type="button" className="danger-link" onClick={removeProfileImage} disabled={busy}>Remove DP</button> : null}
          </div>
        </div>
      </div>
      <div className="section-head">
        <div>
          <h3>Photos and Videos</h3>
          <p>Uploaded media appears on your public customer profile.</p>
        </div>
        <label className="upload-action">
          <UploadCloud size={16} />
          <span>{busy ? "Uploading..." : "Upload"}</span>
          <input type="file" accept="image/*,video/*" multiple onChange={upload} disabled={busy} />
        </label>
      </div>
      {message ? <div className={message.includes("uploaded") || message.includes("removed") ? "notice ok" : "error"}>{message}</div> : null}
      <MediaGallery portfolio={tailor.portfolio} onRemove={remove} />
    </section>
  );
}

function TailorOffersPanel({ offers, reload }) {
  const [form, setForm] = useState({ title: "", body: "", discount: "", expiresAt: "" });
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  function update(key, value) {
    setForm((old) => ({ ...old, [key]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const payload = {
        title: form.title,
        body: form.body,
        discount: form.discount || null,
        expiresAt: form.expiresAt || null,
      };
      if (file) {
        if (!file.type.startsWith("image/") && !file.type.startsWith("video/")) {
          throw new Error("Offer media must be a photo or video");
        }
        if (file.size > 15 * 1024 * 1024) {
          throw new Error("Offer media must be 15 MB or smaller");
        }
        payload.mediaName = file.name;
        payload.mediaType = file.type;
        payload.dataUrl = await readFileAsDataUrl(file);
      }
      await api.createTailorOffer(payload);
      setForm({ title: "", body: "", discount: "", expiresAt: "" });
      setFile(null);
      setMessage("Offer posted. Followers will see this in their customer updates.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
      event.target.reset();
    }
  }

  async function remove(offerId) {
    if (!confirm("Deactivate this offer?")) return;
    setBusy(true);
    setMessage("");
    try {
      await api.deleteTailorOffer(offerId);
      setMessage("Offer deactivated.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="section-block no-top">
      <div className="section-head">
        <div>
          <h3>Offers</h3>
          <p>Followers receive an in-app update when you post a new offer.</p>
        </div>
      </div>
      <form className="offer-form" onSubmit={submit}>
        <label>Offer title<input value={form.title} onChange={(e) => update("title", e.target.value)} placeholder="Festival blouse stitching offer" required /></label>
        <label>Discount / label<input value={form.discount} onChange={(e) => update("discount", e.target.value)} placeholder="10% off this week" /></label>
        <label className="span-2">Offer details<textarea value={form.body} onChange={(e) => update("body", e.target.value)} placeholder="Share what customers can book, pricing note, or timing." required /></label>
        <label>Valid until<input type="date" value={form.expiresAt} onChange={(e) => update("expiresAt", e.target.value)} /></label>
        <label>Photo or video<input type="file" accept="image/*,video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label>
        <button className="primary-btn" disabled={busy}>{busy ? "Posting..." : "Post Offer"}</button>
      </form>
      {message ? <div className={message.includes("posted") || message.includes("deactivated") ? "notice ok" : "error"}>{message}</div> : null}
      <OfferList offers={offers} onRemove={remove} />
    </section>
  );
}

const SERVICE_CATEGORIES = ["Blouse", "Shirt", "Pant", "Combo", "Other"];

function TailorServicesPanel() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ serviceName: "", category: "Blouse", price: "", isCombo: false, comboItems: "", description: "" });
  const [editingId, setEditingId] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const rows = await api.myServices();
      setServices(rows.map(normalizeService));
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function update(key, value) {
    setForm((old) => ({ ...old, [key]: value }));
  }

  function resetForm() {
    setEditingId("");
    setForm({ serviceName: "", category: "Blouse", price: "", isCombo: false, comboItems: "", description: "" });
  }

  function payloadFromForm() {
    return {
      serviceName: form.serviceName,
      category: form.category,
      price: Number(form.price || 0),
      isCombo: form.isCombo,
      comboItems: form.isCombo ? form.comboItems.split(",").map((x) => x.trim()).filter(Boolean) : [],
      description: form.description || null,
    };
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      if (editingId) {
        await api.updateService(editingId, payloadFromForm());
        setMessage("Service updated.");
      } else {
        await api.createService(payloadFromForm());
        setMessage("Service added.");
      }
      resetForm();
      await load();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  function startEdit(service) {
    setEditingId(servicePatchId(service));
    setMessage("");
    setForm({
      serviceName: service.name,
      category: service.category || "Other",
      price: String(service.price || ""),
      isCombo: service.isCombo,
      comboItems: (service.comboItems || []).join(", "),
      description: service.description || "",
    });
  }

  async function toggleActive(service) {
    setBusy(true);
    setMessage("");
    try {
      if (service.isActive) {
        await api.deleteService(servicePatchId(service));
        setMessage("Service deactivated.");
      } else {
        await api.updateService(servicePatchId(service), { isActive: true });
        setMessage("Service reactivated.");
      }
      await load();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="section-block no-top">
      <div className="section-head">
        <div>
          <h3>Services</h3>
          <p>What you stitch and at what price -- shown on your public profile before a customer books.</p>
        </div>
      </div>
      <form className="offer-form" onSubmit={submit}>
        <div className="span-2 form-subhead">
          <strong>{editingId ? "Edit Service" : "Add Service"}</strong>
          {editingId ? <button type="button" className="secondary-btn" onClick={resetForm} disabled={busy}>Cancel Edit</button> : null}
        </div>
        <label>Service name<input value={form.serviceName} onChange={(e) => update("serviceName", e.target.value)} placeholder="Blouse Stitching" required /></label>
        <label>
          Category
          <select value={form.category} onChange={(e) => update("category", e.target.value)}>
            {SERVICE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label>Price (Rs.)<input type="number" min="1" value={form.price} onChange={(e) => update("price", e.target.value)} required /></label>
        <label className="check-row">
          <input type="checkbox" checked={form.isCombo} onChange={(e) => update("isCombo", e.target.checked)} />
          This is a combo
        </label>
        {form.isCombo ? (
          <label className="span-2">Combo items (comma separated)<input value={form.comboItems} onChange={(e) => update("comboItems", e.target.value)} placeholder="Blouse, Petticoat" /></label>
        ) : null}
        <label className="span-2">Description<textarea value={form.description} onChange={(e) => update("description", e.target.value)} /></label>
        <button className="primary-btn" disabled={busy}>{busy ? "Saving..." : editingId ? "Save Changes" : "Add Service"}</button>
      </form>
      {message ? <div className={/(added|updated|reactivated|deactivated)/i.test(message) ? "notice ok" : "error"}>{message}</div> : null}
      {loading ? (
        <Empty text="Loading services..." />
      ) : services.length ? (
        <PaginatedCards
          items={services}
          pageSize={5}
          className="record-list"
          label="services"
          renderItem={(service) => (
            <article className="record-card service-row">
              <div className="record-card-head">
                <Tag size={16} />
                <strong>{service.name}</strong>
                {service.category ? <span className="pill">{service.category}</span> : null}
                {!service.isActive ? <span className="pill danger">Inactive</span> : null}
              </div>
              <p className="price-tag">{money(service.price)}</p>
              {service.isCombo && service.comboItems?.length ? <small>Includes: {service.comboItems.join(", ")}</small> : null}
              {service.description ? <p>{service.description}</p> : null}
              <div className="inline-actions">
                <button type="button" onClick={() => startEdit(service)} disabled={busy}>
                  <Pencil size={14} /> Edit
                </button>
                <button type="button" className={service.isActive ? "danger-link" : "ok-link"} onClick={() => toggleActive(service)} disabled={busy}>
                  {service.isActive ? <><Trash2 size={14} /> Deactivate</> : "Reactivate"}
                </button>
              </div>
            </article>
          )}
        />
      ) : (
        <Empty text="No services added yet." />
      )}
    </section>
  );
}

function TailorFollowersPanel({ followers }) {
  return (
    <section className="section-block no-top">
      <div className="section-head">
        <div>
          <h3>Followers</h3>
          <p>Customer name, profile picture and profile ID are shown for follower context.</p>
        </div>
      </div>
      <PaginatedCards
        items={followers}
        pageSize={8}
        className="follower-grid"
        label="followers"
        emptyText="No followers yet. Customers can follow you from your public profile."
        renderItem={(customer) => (
            <article className="follower-card">
              <CustomerAvatar customer={customer} size="lg" />
              <div>
                <strong>{customer.customerName || customer.name || "Customer"}</strong>
                <small>Profile ID {customer.customerProfileId || customer.id || "-"}</small>
                {customer.customerPhone ? <small>{customer.customerPhone}</small> : null}
                <small>Followed {fmtDate(customer.followedAt)}</small>
              </div>
            </article>
        )}
      />
    </section>
  );
}

function Updates({ title, rows }) {
  return (
    <section className="section-block">
      <h3>{title}</h3>
      <ViewMoreGrid
        items={rows}
        initial={8}
        step={8}
        className="updates-list"
        label="updates"
        emptyText="No updates yet."
        renderItem={(row) => <div className="update-item"><strong>{row.title}</strong><p>{row.body}</p><small>{fmtDate(row.ts)}</small></div>}
      />
    </section>
  );
}

function TailorRequests({ rows, reload }) {
  const pending = rows.filter((r) => r.status === "PENDING");
  const other = rows.filter((r) => r.status !== "PENDING");

  async function accept(row) {
    if (!confirm("Accept this request and create an order?")) return;
    await api.acceptRequest(row.id);
    reload();
  }

  async function reject(row) {
    const reason = prompt("Reject reason:", "Cannot take this order now") || "Rejected by tailor";
    await api.rejectRequest(row.id, reason);
    reload();
  }

  return (
    <section className="section-block">
      <h3>New Requests</h3>
      {pending.length ? <Table columns={["Request", "Customer Area", "Service", "Qty", "Preferred", "Measurement", "Actions"]} rows={pending.map((r) => [r.requirement_code, r.customer_area || "-", r.tailor_service_name || r.service_name, r.quantity, fmtDay(r.preferred_date), r.measurement_mode, <div className="inline-actions"><button onClick={() => accept(r)}>Accept</button><button className="danger-link" onClick={() => reject(r)}>Reject</button></div>])} /> : <Empty text="No new requests." />}
      <h3>Accepted / Rejected / Closed Requests</h3>
      {other.length ? <Table columns={["Request", "Customer", "Status", "Service", "Responded"]} rows={other.map((r) => [r.requirement_code, r.customer_name, <StatusPill value={r.status} />, r.tailor_service_name || r.service_name, fmtDate(r.responded_at || r.ts)])} /> : <Empty />}
    </section>
  );
}

function TailorWaitingListPanel({ reloadDashboard }) {
  const [rows, setRows] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  async function load() {
    setLoading(true);
    setMessage("");
    try {
      setRows(await api.tailorWaitingList());
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function confirm(row) {
    setBusy(row.id);
    setMessage("");
    try {
      const res = await api.tailorConfirmBooking(row.id);
      setMessage(res.message || "Booking confirmed.");
      await load();
      await reloadDashboard();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="section-block">
      <div className="section-head">
        <div>
          <h3>Waiting List</h3>
          <p>When you become free, manually choose which waiting customer to confirm next.</p>
        </div>
        <button type="button" className="secondary-btn" onClick={load}>Refresh</button>
      </div>
      {message ? <div className={message.includes("confirmed") || message.includes("pending") ? "notice ok" : "error"}>{message}</div> : null}
      {loading ? <div className="loading">Loading waiting list...</div> : rows.length ? (
        <PaginatedCards
          items={rows}
          pageSize={5}
          className="record-list"
          label="waiting customers"
          renderItem={(row) => (
            <article className="record-card waiting-card">
              <div>
                <strong>{row.code}</strong>
                <p>{row.customerName || row.customer_name} - {row.serviceName || row.service_name}</p>
                <small>{row.measurementMode || row.measurement_mode}</small>
                {row.customerLocationAddress || row.customer_location_address ? <small>{row.customerLocationAddress || row.customer_location_address}</small> : null}
              </div>
              <div>
                <span className="waiting-pill"><span className="live-dot" /> Waiting</span>
                <button type="button" className="primary-btn compact-action" onClick={() => confirm(row)} disabled={busy === row.id}>{busy === row.id ? "Confirming..." : "Confirm Next"}</button>
              </div>
            </article>
          )}
        />
      ) : <Empty text="No customers are waiting right now." />}
    </section>
  );
}

function TailorOrders({ rows, reload }) {
  const [filter, setFilter] = useState("in_progress");

  const cancelledOrders = rows.filter((order) => String(order?.status || "").toLowerCase() === "cancelled");
  const completedOrders = rows.filter((order) => isCompletedOrder(order) && String(order?.status || "").toLowerCase() !== "cancelled");
  const inProgressOrders = rows.filter((order) => !isCompletedOrder(order) && String(order?.status || "").toLowerCase() !== "cancelled");
  const filters = [
    ["in_progress", "In progress", inProgressOrders],
    ["completed", "Completed", completedOrders],
    ["cancelled", "Cancelled", cancelledOrders],
    ["all", "All orders", rows],
  ];
  const activeFilter = filters.find(([key]) => key === filter) || filters[0];
  const activeRows = activeFilter[2];

  async function addCharge(order) {
    if (isCompletedOrder(order)) return;
    const description = prompt("Charge description:", "Extra fitting");
    if (!description) return;
    const amount = Number(prompt("Amount:", "100"));
    if (!amount) return;
    const reason = prompt("Reason:", "Additional work") || "";
    await api.addCharge(order.id, { description, amount, reason });
    reload();
  }

  async function markMeasurementDone(order) {
    if (isCompletedOrder(order)) return;
    await api.measurementDone(order.id);
    reload();
  }

  return (
    <section className="section-block">
      <div className="section-head">
        <div>
          <h3>Orders</h3>
          <p>Filter active, completed and cancelled orders without losing the full order controls.</p>
        </div>
      </div>
      {rows.length ? (
        <>
          <div className="order-filter-tabs" role="tablist" aria-label="Tailor order filters">
            {filters.map(([key, label, items]) => (
              <button
                type="button"
                key={key}
                className={filter === key ? "active" : ""}
                onClick={() => setFilter(key)}
                role="tab"
                aria-selected={filter === key}
              >
                <span>{label}</span>
                <b>{items.length}</b>
              </button>
            ))}
          </div>
          {activeRows.length ? (
            <Table columns={["Order", "Customer", "Status", "Payment", "Due", "Total", "Actions"]} label="orders" rows={activeRows.map((o) => [
              <><strong>{o.code}</strong><small>{o.service_name}</small></>,
              <><span>{o.customer_name}</span><small>{o.customer_phone || ""}</small></>,
              <StatusPill value={o.status} />,
              <StatusPill value={o.payment_status} />,
              fmtDay(o.expected_completion),
              money(o.total),
              <TailorOrderActions order={o} reload={reload} onCharge={() => addCharge(o)} onMeasurementDone={() => markMeasurementDone(o)} />,
            ])} />
          ) : <Empty text={`No ${activeFilter[1].toLowerCase()} orders right now.`} />}
        </>
      ) : <Empty text="No orders yet." />}
    </section>
  );
}

function isCompletedOrder(order) {
  const status = String(order?.status || "").toLowerCase();
  return status === "completed" || Boolean(order?.completed_at || order?.completedAt);
}

function TailorOrderActions({ order, reload, onCharge, onMeasurementDone }) {
  const [stage, setStage] = useState(order.tracker_stage || order.trackerStage || "Order Placed");
  const [note, setNote] = useState("");
  const [otp, setOtp] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const paid = String(order.payment_status || order.paymentStatus || "").toLowerCase() === "paid";
  const completed = isCompletedOrder(order);

  useEffect(() => {
    setStage(order.tracker_stage || order.trackerStage || "Order Placed");
  }, [order.tracker_stage, order.trackerStage, order.id]);
  const stageOptions = bookingTrackerStages.filter((value) => value !== "Delivered");

  async function update() {
    if (completed) return;
    setBusy(true);
    setMessage("");
    try {
      await api.updateBookingStage(order.id, { trackerStage: stage, note });
      setNote("");
      reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendOtp() {
    if (completed) return;
    setBusy(true);
    setMessage("");
    try {
      const res = await api.sendDeliveryOtp(order.id);
      setMessage(res.message || "Delivery OTP sent.");
      reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp() {
    if (completed) return;
    setBusy(true);
    setMessage("");
    try {
      const res = await api.verifyDeliveryOtp(order.id, otp);
      setMessage(res.message || "Delivery OTP verified.");
      setOtp("");
      reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (completed) {
    return (
      <div className="completed-order-note">
        <CheckCircle2 size={16} />
        <span>Closed after handover OTP</span>
      </div>
    );
  }

  return (
    <div className="order-actions tracker-actions">
      <select value={stage} onChange={(e) => setStage(e.target.value)} disabled={busy}>
        {stageOptions.map((value) => <option key={value} value={value}>{value}</option>)}
      </select>
      <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Status note" disabled={busy} />
      <button onClick={update} disabled={busy}>Send Update</button>
      {!completed && ["auto_approved", "measurement_pending", "tailor_confirmed"].includes(order.status) ? <button onClick={onMeasurementDone} disabled={busy}>Measurement Done</button> : null}
      <button onClick={onCharge} disabled={busy}>Charge</button>
      <div className={paid ? "delivery-otp-box unlocked" : "delivery-otp-box locked"}>
        <small>{paid ? "Delivery OTP enabled." : "Complete payment to enable delivery OTP."}</small>
        <button type="button" onClick={sendOtp} disabled={!paid || busy}>Send OTP</button>
        <input value={otp} onChange={(e) => setOtp(cleanDigits(e.target.value))} inputMode="numeric" maxLength={6} placeholder="Handover OTP" disabled={!paid || busy} />
        <button type="button" onClick={verifyOtp} disabled={!paid || busy || !otp}>Verify OTP</button>
      </div>
      {message ? <small className={message.includes("sent") || message.includes("verified") ? "field-success" : "field-error"}>{message}</small> : null}
    </div>
  );
}

function AdminApp({ onLogout }) {
  const { language, setLanguage, t } = useLanguage();
  const [section, setSection] = useAppHistoryState("adminSection", "dashboard");
  const [data, setData] = useState({ metrics: {}, customers: [], tailors: [], requests: [], orders: [], payments: [], paymentIntents: [], withdrawalRequests: [], reviews: [], supportTickets: [], complaints: [], audit: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const [metrics, customers, tailors, requests, orders, payments, paymentIntents, withdrawalRequests, reviews, supportTickets, complaints, audit] = await Promise.all([
        api.metrics(),
        api.customers(),
        api.tailors(),
        api.bookingRequests(),
        api.orders(),
        api.payments(),
        api.adminPaymentIntents(),
        api.adminWithdrawalRequests(),
        api.reviews(),
        api.supportTickets(),
        api.complaints(),
        api.audit(),
      ]);
      setData({ metrics, customers, tailors, requests, orders, payments, paymentIntents, withdrawalRequests, reviews, supportTickets, complaints, audit });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const includes = (row) => !needle || JSON.stringify(row).toLowerCase().includes(needle);
    return {
      customers: data.customers.filter(includes),
      tailors: data.tailors.filter(includes),
      requests: data.requests.filter(includes),
      orders: data.orders.filter(includes),
      payments: data.payments.filter(includes),
      paymentIntents: data.paymentIntents.filter(includes),
      withdrawalRequests: data.withdrawalRequests.filter(includes),
      reviews: data.reviews.filter(includes),
      supportTickets: data.supportTickets.filter(includes),
      complaints: data.complaints.filter(includes),
      audit: data.audit.filter(includes),
    };
  }, [data, query]);

  const activeSection = adminSections.find(([id]) => id === section) || adminSections[0];
  const ActiveIcon = activeSection?.[2] || Shield;
  const activeLabel = adminSectionLabel(activeSection[0], activeSection[1], t);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-row compact">
          <div className="brand-mark">TH</div>
          <div><h1>{t("dashboard.admin.title", "Admin")}</h1><p>{t("dashboard.admin.subtitle", "Platform operations")}</p></div>
        </div>
        <nav>
          {adminSections.map(([id, label, Icon]) => (
            <button key={id} className={section === id ? "nav-item active" : "nav-item"} onClick={() => setSection(id)}>
              <Icon size={17} /><span>{adminSectionLabel(id, label, t)}</span>
              {id === "approvals" && data.metrics.pending_tailors ? <b>{data.metrics.pending_tailors}</b> : null}
              {id === "requests" && data.metrics.booking_requests ? <b>{data.metrics.booking_requests}</b> : null}
              {id === "support" && data.metrics.support_tickets ? <b>{data.metrics.support_tickets}</b> : null}
              {id === "complaints" && data.metrics.complaints ? <b>{data.metrics.complaints}</b> : null}
            </button>
          ))}
        </nav>
      </aside>
      <main className="main">
        <header className="topbar">
          <div><div className="eyebrow"><ActiveIcon size={14} /> {activeLabel}</div><h2>{section === "dashboard" ? t("dashboard.platform", "Platform dashboard") : activeLabel}</h2></div>
          <div className="top-actions">
            <LanguageSelect language={language} setLanguage={setLanguage} />
            <label className="search"><Search size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("admin.searchPlaceholder", "Search current data")} /></label>
            <button className="icon-btn" onClick={loadAll} title={t("common.refresh", "Refresh")}><RefreshCw size={17} /></button>
            <button className="icon-btn" onClick={onLogout} title={t("common.logout", "Logout")}><LogOut size={17} /></button>
          </div>
        </header>
        {error ? <div className="error banner">{error}</div> : null}
        {loading ? <div className="loading">{t("admin.loading", "Loading live data...")}</div> : null}
        {section === "dashboard" && <Dashboard metrics={data.metrics} />}
        {section === "customers" && <Customers rows={filtered.customers} reload={loadAll} />}
        {section === "tailors" && <Tailors rows={filtered.tailors} reload={loadAll} />}
        {section === "approvals" && <Approvals rows={filtered.tailors.filter((t) => t.approvalStatus === "PENDING_APPROVAL")} reload={loadAll} />}
        {section === "requests" && <AdminRequests rows={filtered.requests} />}
        {section === "orders" && <Orders rows={filtered.orders} reload={loadAll} />}
        {section === "payments" && <Payments rows={filtered.payments} intents={filtered.paymentIntents} withdrawals={filtered.withdrawalRequests} reload={loadAll} />}
        {section === "finance" && <AdminFinancePanel />}
        {section === "referrals" && <AdminReferralTreePanel tailors={filtered.tailors} />}
        {section === "customerReferrals" && <AdminCustomerReferralTreePanel customers={filtered.customers} />}
        {section === "disputes" && <AdminDisputesPanel />}
        {section === "reviews" && <Reviews rows={filtered.reviews} reload={loadAll} />}
        {section === "support" && <AdminSupport rows={filtered.supportTickets} reload={loadAll} />}
        {section === "complaints" && <Complaints rows={filtered.complaints} reload={loadAll} />}
        {section === "audit" && <Audit rows={filtered.audit} />}
      </main>
    </div>
  );
}

function tailorTreeId(row) {
  return row?.tailorId || row?.tailor_id || row?.id || "";
}

function tailorTreeLabel(row) {
  const id = tailorTreeId(row);
  return [row?.shop, row?.ownerName || row?.owner_name].filter(Boolean).join(" - ") || id;
}

function AdminReferralTreePanel({ tailors }) {
  const [selected, setSelected] = useState("");
  const [treeData, setTreeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!selected && tailors.length) {
      setSelected(tailorTreeId(tailors[0]));
    }
  }, [tailors, selected]);

  async function loadTree(nextSelected = selected) {
    if (!nextSelected) return;
    setLoading(true);
    setMessage("");
    try {
      const nextTree = await api.adminReferralTree(nextSelected);
      setTreeData(nextTree);
    } catch (err) {
      setTreeData(null);
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadTree(selected); }, [selected]);

  if (!tailors.length) {
    return <Empty text="No tailors available for referral tree lookup." />;
  }

  return (
    <section className="section-block no-top referral-tree-panel">
      <div className="section-head">
        <div>
          <h3>Referral Tree</h3>
          <p>Admin-only recursive view of who referred whom across the tailor network.</p>
        </div>
        <button type="button" className="secondary-btn" onClick={() => loadTree()} disabled={loading}>Refresh Tree</button>
      </div>
      {message ? <div className="error banner">{message}</div> : null}
      <div className="record-card referral-tree-controls">
        <Field label="Root tailor">
          <select value={selected} onChange={(event) => setSelected(event.target.value)}>
            {tailors.map((tailor) => {
              const id = tailorTreeId(tailor);
              return <option value={id} key={id}>{tailorTreeLabel(tailor)}</option>;
            })}
          </select>
        </Field>
        <div className="referral-tree-stat">
          <span>Total in tree</span>
          <strong>{treeData?.total_tailors ?? treeData?.totalTailors ?? 0}</strong>
        </div>
      </div>
      {loading ? <div className="loading">Loading referral tree...</div> : null}
      {treeData?.tree ? (
        <ul className="referral-tree">
          <ReferralTreeNode node={treeData.tree} />
        </ul>
      ) : !loading ? <Empty text="No referral tree loaded yet." /> : null}
    </section>
  );
}

function ReferralTreeNode({ node }) {
  const children = node.children || [];
  return (
    <li>
      <div className="referral-node-card">
        <div>
          <strong>{node.shop || node.fullName || node.ownerName || "Tailor"}</strong>
          <span>{node.ownerName || node.owner_name || "Owner not set"}</span>
        </div>
        <div>
          <small>Code</small>
          <b>{node.referralCode || node.referral_code || "-"}</b>
        </div>
        <div>
          <small>Direct</small>
          <b>{node.directReferrals ?? node.direct_referrals ?? children.length}</b>
        </div>
      </div>
      {children.length ? (
        <ul>
          {children.map((child) => <ReferralTreeNode key={child.tailorId || child.tailor_id} node={child} />)}
        </ul>
      ) : null}
    </li>
  );
}

function customerTreeId(row) {
  return row?.customerId || row?.customer_id || row?.id || "";
}

function customerTreeLabel(row) {
  const id = customerTreeId(row);
  return [row?.name, row?.phone].filter(Boolean).join(" - ") || id;
}

function AdminCustomerReferralTreePanel({ customers }) {
  const [selected, setSelected] = useState("");
  const [treeData, setTreeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!selected && customers.length) {
      setSelected(customerTreeId(customers[0]));
    }
  }, [customers, selected]);

  async function loadTree(nextSelected = selected) {
    if (!nextSelected) return;
    setLoading(true);
    setMessage("");
    try {
      setTreeData(await api.adminCustomerReferralTree(nextSelected));
    } catch (err) {
      setTreeData(null);
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadTree(selected); }, [selected]);

  if (!customers.length) {
    return <Empty text="No customers available for referral tree lookup." />;
  }

  return (
    <section className="section-block no-top referral-tree-panel">
      <div className="section-head">
        <div>
          <h3>Customer Referral Tree</h3>
          <p>Admin-only recursive view of valid phone-number-unique customer referrals.</p>
        </div>
        <button type="button" className="secondary-btn" onClick={() => loadTree()} disabled={loading}>Refresh Tree</button>
      </div>
      {message ? <div className="error banner">{message}</div> : null}
      <div className="record-card referral-tree-controls">
        <Field label="Root customer">
          <select value={selected} onChange={(event) => setSelected(event.target.value)}>
            {customers.map((customer) => {
              const id = customerTreeId(customer);
              return <option value={id} key={id}>{customerTreeLabel(customer)}</option>;
            })}
          </select>
        </Field>
        <div className="referral-tree-stat">
          <span>Total in tree</span>
          <strong>{treeData?.total_customers ?? treeData?.totalCustomers ?? 0}</strong>
        </div>
      </div>
      {loading ? <div className="loading">Loading customer referral tree...</div> : null}
      {treeData?.tree ? (
        <ul className="referral-tree">
          <CustomerReferralTreeNode node={treeData.tree} />
        </ul>
      ) : !loading ? <Empty text="No customer referral tree loaded yet." /> : null}
    </section>
  );
}

function CustomerReferralTreeNode({ node }) {
  const children = node.children || [];
  return (
    <li>
      <div className="referral-node-card">
        <div className="tailor-identity">
          <CustomerAvatar customer={{ customerProfileId: node.customerId || node.customer_id, profileImage: node.profileImage || node.profile_image }} size="sm" />
          <div>
            <strong>{node.name || "Customer"}</strong>
            <span>{node.phone || node.email || "Contact not set"}</span>
          </div>
        </div>
        <div>
          <small>Code</small>
          <b>{node.referralCode || node.referral_code || "-"}</b>
        </div>
        <div>
          <small>Valid</small>
          <b>{node.validReferrals ?? node.valid_referrals ?? children.length}</b>
        </div>
      </div>
      {children.length ? (
        <ul>
          {children.map((child) => <CustomerReferralTreeNode key={child.customerId || child.customer_id} node={child} />)}
        </ul>
      ) : null}
    </li>
  );
}

function AdminFinancePanel() {
  const [settings, setSettings] = useState({ commissionPercentage: "", gstPercentage: "", platformFeePercentage: "" });
  const [filters, setFilters] = useState({ dateFrom: "", dateTo: "" });
  const [wallet, setWallet] = useState({ transactions: [] });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  function normalizeSettings(row) {
    return {
      commissionPercentage: row?.commissionPercentage ?? row?.commission_percentage ?? "20.00",
      gstPercentage: row?.gstPercentage ?? row?.gst_percentage ?? "18.00",
      platformFeePercentage: row?.platformFeePercentage ?? row?.platform_fee_percentage ?? "2.00",
    };
  }

  async function load() {
    setLoading(true);
    setMessage("");
    try {
      const [settingsData, walletData] = await Promise.all([
        api.adminFinanceSettings(),
        api.adminFinanceWallet(filters),
      ]);
      setSettings(normalizeSettings(settingsData));
      setWallet(walletData);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function saveSettings(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const updated = await api.updateAdminFinanceSettings({
        commission_percentage: Number(settings.commissionPercentage || 0),
        gst_percentage: Number(settings.gstPercentage || 0),
        platform_fee_percentage: Number(settings.platformFeePercentage || 0),
      });
      setSettings(normalizeSettings(updated));
      setMessage("Finance settings updated. New payments will use these rates.");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function applyFilters(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      setWallet(await api.adminFinanceWallet(filters));
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv() {
    setBusy(true);
    setMessage("");
    try {
      const csvText = await api.exportAdminFinanceWallet(filters);
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "admin-wallet-transactions.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setMessage("Transaction log exported.");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <section className="section-block no-top"><div className="loading">Loading finance engine...</div></section>;
  }

  const transactions = wallet.transactions || [];

  return (
    <section className="section-block no-top finance-panel">
      <div className="section-head">
        <div>
          <h3>Finance Engine</h3>
          <p>Percentages are read in real time from platform settings for new payments and completed deliveries.</p>
        </div>
        <button type="button" className="secondary-btn" onClick={load} disabled={busy}>Refresh</button>
      </div>
      {message ? <div className={message.includes("updated") || message.includes("exported") ? "notice ok" : "error banner"}>{message}</div> : null}
      <div className="finance-grid">
        <form className="record-card stack-form" onSubmit={saveSettings}>
          <h3>Admin Settings</h3>
          <Field label="Tailor commission %">
            <input type="number" min="0" step="0.01" value={settings.commissionPercentage} onChange={(event) => setSettings((old) => ({ ...old, commissionPercentage: event.target.value }))} />
          </Field>
          <Field label="GST %">
            <input type="number" min="0" step="0.01" value={settings.gstPercentage} onChange={(event) => setSettings((old) => ({ ...old, gstPercentage: event.target.value }))} />
          </Field>
          <Field label="Platform fee %">
            <input type="number" min="0" step="0.01" value={settings.platformFeePercentage} onChange={(event) => setSettings((old) => ({ ...old, platformFeePercentage: event.target.value }))} />
          </Field>
          <button className="primary-btn" disabled={busy}>Save Percentages</button>
        </form>
        <div className="wallet-card">
          <div>
            <small>Admin wallet balance</small>
            <strong>{money(wallet.balance)}</strong>
            <span>Wallet ID {String(wallet.wallet_id || wallet.walletId || "").slice(0, 8) || "-"}</span>
          </div>
          <div className="wallet-qr-tile">
            <CreditCard size={44} />
            <span>Platform collections</span>
          </div>
        </div>
      </div>
      <div className="kpi-grid">
        <Kpi label="Commission Collected" value={money(wallet.commissionTotal ?? wallet.commission_total)} icon={CreditCard} />
        <Kpi label="GST / Platform Fees" value={money(wallet.gstPlatformChargeTotal ?? wallet.gst_platform_charge_total)} icon={CreditCard} />
      </div>
      <form className="record-card finance-filter-row" onSubmit={applyFilters}>
        <Field label="From">
          <input type="date" value={filters.dateFrom} onChange={(event) => setFilters((old) => ({ ...old, dateFrom: event.target.value }))} />
        </Field>
        <Field label="To">
          <input type="date" value={filters.dateTo} onChange={(event) => setFilters((old) => ({ ...old, dateTo: event.target.value }))} />
        </Field>
        <button className="secondary-btn" disabled={busy}>Apply</button>
        <button type="button" className="secondary-btn" onClick={exportCsv} disabled={busy || !transactions.length}>Export CSV</button>
      </form>
      {transactions.length ? (
        <Table columns={["Type", "Amount", "Order", "Tailor", "Customer", "Created"]} rows={transactions.map((row) => [
          <StatusPill value={row.type} />,
          money(row.amount),
          <><strong>{row.orderCode || row.order_code || "-"}</strong><small>{row.sourceBookingId || row.source_booking_id}</small></>,
          row.shop || "-",
          row.customerName || row.customer_name || "-",
          fmtDate(row.createdAt || row.created_at),
        ])} />
      ) : <Empty text="No admin wallet transactions for the selected range." />}
    </section>
  );
}

function AdminDisputesPanel() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  async function load() {
    setLoading(true);
    setMessage("");
    try {
      setRows(await api.adminDisputes());
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function update(row) {
    const status = (prompt("Status: open, in_review, resolved, rejected", row.status) || row.status).toLowerCase();
    const resolutionNotes = prompt("Resolution notes:", row.resolutionNotes || row.resolution_notes || "") || "";
    const refundRaw = prompt("Optional refund credit amount:", String(row.refundAmount || row.refund_amount || 0));
    const refundAmount = refundRaw === null || refundRaw.trim() === "" ? null : Number(refundRaw);
    setMessage("");
    try {
      await api.patchAdminDispute(row.id, { status, resolutionNotes, refundAmount });
      setMessage("Dispute updated.");
      await load();
    } catch (err) {
      setMessage(err.message);
    }
  }

  if (loading) {
    return <section className="section-block no-top"><div className="loading">Loading disputes...</div></section>;
  }

  if (!rows.length) {
    return (
      <section className="section-block no-top">
        <div className="section-head">
          <div><h3>Dispute Queue</h3><p>Customer delivery disputes appear here for admin review.</p></div>
          <button type="button" className="secondary-btn" onClick={load}>Refresh</button>
        </div>
        {message ? <div className={message.includes("updated") ? "notice ok" : "error banner"}>{message}</div> : null}
        <Empty text="No disputes yet." />
      </section>
    );
  }

  return (
    <section className="section-block no-top">
      <div className="section-head">
        <div><h3>Dispute Queue</h3><p>Review customer disputes and optionally credit a manual refund to the customer wallet.</p></div>
        <button type="button" className="secondary-btn" onClick={load}>Refresh</button>
      </div>
      {message ? <div className={message.includes("updated") ? "notice ok" : "error banner"}>{message}</div> : null}
      <Table columns={["Dispute", "Customer", "Tailor", "Status", "Refund", "Photo", "Actions"]} rows={rows.map((row) => [
        <><strong>{row.orderCode || row.order_code || row.bookingId}</strong><small>{row.reason}</small></>,
        <><span>{row.customerName || row.customer_name}</span><small>{row.customerPhone || row.customer_phone || row.customerEmail || row.customer_email || "-"}</small></>,
        <><span>{row.shop || "-"}</span><small>{row.ownerName || row.owner_name || ""}</small></>,
        <StatusPill value={row.status} />,
        money(row.refundAmount || row.refund_amount),
        row.photoUrl || row.photo_url ? <a href={assetUrl(row.photoUrl || row.photo_url)} target="_blank" rel="noreferrer">View</a> : "-",
        <button className="ok-link" onClick={() => update(row)}>Update</button>,
      ])} />
    </section>
  );
}

function Kpi({ label, value, icon: Icon }) {
  return <div className="kpi"><Icon size={18} /><strong>{value ?? 0}</strong><span>{label}</span></div>;
}

function Dashboard({ metrics }) {
  const cards = [
    ["Total Customers", metrics.customers, UsersRound],
    ["Active Customers", metrics.active_customers, CheckCircle2],
    ["Suspended Customers", metrics.suspended_customers, Ban],
    ["Total Tailors", metrics.tailors, Scissors],
    ["Pending Tailor Approvals", metrics.pending_tailors, BadgeCheck],
    ["Verified Tailors", metrics.verified_tailors, BadgeCheck],
    ["Active Tailors", metrics.active_tailors, CheckCircle2],
    ["Suspended Tailors", metrics.suspended_tailors, Ban],
    ["Total Booking Requests", metrics.booking_requests, ClipboardList],
    ["Active Orders", metrics.active_orders, ClipboardList],
    ["Completed Orders", metrics.completed_orders, CheckCircle2],
    ["Cancelled Orders", metrics.cancelled_orders, XCircle],
    ["Total Payments", money(metrics.total_payments), CreditCard],
    ["Pending Payments", metrics.pending_payments, CreditCard],
    ["Open Support Tickets", metrics.support_tickets, AlertTriangle],
    ["Customer Support", metrics.customer_support, UsersRound],
    ["Tailor Support", metrics.tailor_support, Scissors],
    ["Complaints / Issues", metrics.complaints, AlertTriangle],
  ];
  return <div className="kpi-grid">{cards.map(([label, value, Icon]) => <Kpi key={label} label={label} value={value} icon={Icon} />)}</div>;
}

function Customers({ rows, reload }) {
  const [message, setMessage] = useState("");

  async function setStatus(row, status) {
    const reason = prompt(`Reason for ${status.toLowerCase()}:`) || "Admin update";
    if (!confirm(`Confirm customer status change to ${status}?`)) return;
    setMessage("");
    await api.patchCustomer(row.id, { status, reason });
    reload();
  }

  async function remove(row) {
    setMessage("");
    const check = await api.customerDeleteCheck(row.id);
    const msg = `Delete ${row.name}?\nPending requests: ${check.pending_requests}\nActive bookings: ${check.active_bookings}\nOngoing orders: ${check.ongoing_orders}\nPending payments: ${check.pending_payments}`;
    if (!check.safeToDelete) {
      setMessage(msg + "\n\nResolve active work before deleting.");
      return;
    }
    if (!confirm(msg)) return;
    await api.deleteCustomer(row.id, prompt("Deletion reason:") || "Admin deletion");
    reload();
  }

  const content = !rows.length ? <Empty /> : <Table columns={["Customer", "Contact", "Status", "Joined", "Actions"]} rows={rows.map((r) => [
    <><strong>{r.name}</strong><small>{r.id}</small></>,
    <><span>{r.email || "No email"}</span><small>{r.phone}</small></>,
    <StatusPill value={r.status} />,
    fmtDate(r.joined),
    <ActionSet onActive={() => setStatus(r, "ACTIVE")} onSuspend={() => setStatus(r, "SUSPENDED")} onBlock={() => setStatus(r, "BLOCKED")} onDelete={() => remove(r)} />,
  ])} />;

  return <>
    {message ? <div className="error banner" style={{ whiteSpace: "pre-line" }}>{message}</div> : null}
    {content}
  </>;
}

function Tailors({ rows, reload }) {
  const [message, setMessage] = useState("");

  async function setStatus(row, status) {
    const reason = prompt(`Reason for ${status.toLowerCase()}:`) || "Admin update";
    if (!confirm(`Confirm tailor status change to ${status}?`)) return;
    setMessage("");
    await api.patchTailor(row.id, { accountStatus: status, reason });
    reload();
  }

  async function remove(row) {
    setMessage("");
    const check = await api.tailorDeleteCheck(row.id);
    const msg = `Delete ${row.shop}?\nPending requests: ${check.pending_requests}\nActive orders: ${check.active_orders}\nPending deliveries: ${check.pending_deliveries}\nPending payments: ${check.pending_payments}`;
    if (!check.safeToDelete) {
      setMessage(msg + "\n\nResolve active work before deleting.");
      return;
    }
    if (!confirm(msg)) return;
    await api.deleteTailor(row.id, prompt("Deletion reason:") || "Admin deletion");
    reload();
  }

  const content = !rows.length ? <Empty /> : <Table columns={["Tailor", "Business", "Approval", "Availability", "Status", "Actions"]} rows={rows.map((r) => [
    <><strong>{r.shop}</strong><small>{r.ownerName}</small></>,
    <><span>{(r.expertise || []).join(", ") || "No services"}</span><small>{r.email || r.phone}</small></>,
    <StatusPill value={r.approvalStatus} />,
    <StatusPill value={r.availability} />,
    <StatusPill value={r.accountStatus} />,
    <ActionSet onActive={() => setStatus(r, "ACTIVE")} onSuspend={() => setStatus(r, "SUSPENDED")} onBlock={() => setStatus(r, "BLOCKED")} onDelete={() => remove(r)} />,
  ])} />;

  return <>
    {message ? <div className="error banner" style={{ whiteSpace: "pre-line" }}>{message}</div> : null}
    {content}
  </>;
}

function Approvals({ rows, reload }) {
  if (!rows.length) return <Empty />;
  return (
    <PaginatedCards
      items={rows}
      pageSize={6}
      label="approvals"
      renderItem={(r) => (
        <div className="record-card">
          <h3>{r.shop}</h3>
          <p>{r.ownerName} - {(r.expertise || []).join(", ")}</p>
          <p>{r.email || r.phone}</p>
          <div className="actions">
            <button className="ok-btn" onClick={async () => { await api.approveTailor(r.id); reload(); }}>Approve + Verify</button>
            <button className="danger-btn" onClick={async () => { await api.rejectTailor(r.id, prompt("Reject reason:") || "Documents incomplete"); reload(); }}>Reject</button>
          </div>
        </div>
      )}
    />
  );
}

function AdminRequests({ rows }) {
  if (!rows.length) return <Empty />;
  return <Table columns={["Request", "Customer", "Tailor", "Service", "Status", "Preferred"]} rows={rows.map((r) => [
    r.requirement_code,
    <><span>{r.customer_name}</span><small>{r.customer_phone}</small></>,
    r.shop,
    `${r.quantity} x ${r.service_name}`,
    <StatusPill value={r.status} />,
    fmtDay(r.preferred_date),
  ])} />;
}

function Orders({ rows, reload }) {
  if (!rows.length) return <Empty />;
  return <Table columns={["Order", "People", "Status", "Payment", "Total", "Actions"]} rows={rows.map((r) => [
    <><strong>{r.code}</strong><small>{r.service_name}</small></>,
    <><span>{r.customer_name}</span><small>{r.shop}</small></>,
    <StatusPill value={r.status} />,
    <StatusPill value={r.payment_status} />,
    money(r.total),
    <button className="danger-link" onClick={async () => { if (!confirm("Cancel this order?")) return; await api.cancelOrder(r.id, prompt("Reason:") || "Cancelled by admin"); reload(); }}>Cancel</button>,
  ])} />;
}

function Payments({ rows, intents = [], withdrawals = [], reload = () => {} }) {
  const [proofs, setProofs] = useState({});
  const [payoutRefs, setPayoutRefs] = useState({});
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState("");

  const pendingManualIntents = intents.filter((item) => {
    const status = String(item.status || "").toLowerCase();
    const method = String(item.method || "").toLowerCase();
    return status === "pending" && method !== "razorpay";
  });
  const pendingWithdrawals = withdrawals.filter((item) => String(item.status || "").toLowerCase() === "pending_admin_review");

  async function verifyIntent(item) {
    const proofReference = (proofs[item.id] || "").trim();
    if (!proofReference) {
      setMessage("Enter the manual transaction reference before verifying payment.");
      return;
    }
    setBusyId(item.id);
    setMessage("");
    try {
      const res = await api.verifyPaymentIntent(item.id, { proofReference });
      setMessage(res.message || "Payment verified.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusyId("");
    }
  }

  async function rejectIntent(item) {
    setBusyId(item.id);
    setMessage("");
    try {
      const res = await api.rejectPaymentIntent(item.id, { adminNote: "Payment was not confirmed in the business account." });
      setMessage(res.message || "Payment request rejected.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusyId("");
    }
  }

  async function approveWithdrawal(item) {
    const payoutReference = (payoutRefs[item.id] || "").trim();
    if (!payoutReference) {
      setMessage("Enter your manual bank/UPI payout reference before approving withdrawal.");
      return;
    }
    setBusyId(item.id);
    setMessage("");
    try {
      const res = await api.approveWithdrawalRequest(item.id, { payoutReference });
      setMessage(res.message || "Withdrawal approved.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusyId("");
    }
  }

  async function rejectWithdrawal(item) {
    setBusyId(item.id);
    setMessage("");
    try {
      const res = await api.rejectWithdrawalRequest(item.id, { adminNote: "Manual payout could not be processed. Please contact support." });
      setMessage(res.message || "Withdrawal rejected.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusyId("");
    }
  }

  if (!rows.length && !intents.length && !withdrawals.length) return <Empty />;

  return (
    <div className="admin-payment-panel">
      {message ? <div className={message.includes("Enter") || message.includes("not") || message.includes("rejected") ? "error banner" : "notice ok"}>{message}</div> : null}

      <section className="section-block no-top">
        <div className="section-head">
          <div>
            <h3>Manual Payment Verification</h3>
            <p>Use only for offline fallback payments. Razorpay payments verify automatically through signature verification.</p>
          </div>
          <StatusPill value={`${pendingManualIntents.length} pending`} />
        </div>
        {pendingManualIntents.length ? <Table columns={["Order", "Customer", "Reference", "Payable", "Tailor credit", "Expires", "Action"]} rows={pendingManualIntents.map((item) => [
          <><strong>{item.orderCode || item.order_code}</strong><small>{item.shop}</small></>,
          <><span>{item.customerName || item.customer_name}</span><small>{item.customerPhone || item.customer_phone || "-"}</small></>,
          item.paymentReference || item.payment_reference,
          money(item.payableTotal ?? item.payable_total),
          <><span>{money(item.tailorCreditAmount ?? item.tailor_credit_amount)}</span><small>Commission {money(item.commissionAmount ?? item.commission_amount)}</small></>,
          fmtDate(item.expiresAt || item.expires_at),
          <div className="inline-actions finance-actions">
            <input
              value={proofs[item.id] || ""}
              onChange={(event) => setProofs((old) => ({ ...old, [item.id]: event.target.value }))}
              placeholder="Manual txn ref"
            />
            <button type="button" onClick={() => verifyIntent(item)} disabled={busyId === item.id}>Verify</button>
            <button type="button" className="danger-link" onClick={() => rejectIntent(item)} disabled={busyId === item.id}>Reject</button>
          </div>,
        ])} /> : <Empty text="No manual fallback payments waiting for verification." />}
      </section>

      <section className="section-block">
        <div className="section-head">
          <div>
            <h3>Withdrawal Approval Queue</h3>
            <p>Debit the tailor wallet only after you manually pay the tailor from the business account.</p>
          </div>
          <StatusPill value={`${pendingWithdrawals.length} pending`} />
        </div>
        {pendingWithdrawals.length ? <Table columns={["Tailor", "Amount", "Destination", "Wallet", "Requested", "Action"]} rows={pendingWithdrawals.map((item) => [
          <><strong>{item.shop}</strong><small>{item.tailorPhone || item.tailor_phone || item.tailorEmail || item.tailor_email || "-"}</small></>,
          money(item.amount),
          <><span>{item.destinationType || item.destination_type}</span><small>{item.destination}</small></>,
          money(item.walletBalance ?? item.wallet_balance),
          fmtDate(item.requestedAt || item.requested_at),
          <div className="inline-actions finance-actions">
            <input
              value={payoutRefs[item.id] || ""}
              onChange={(event) => setPayoutRefs((old) => ({ ...old, [item.id]: event.target.value }))}
              placeholder="Manual payout ref"
            />
            <button type="button" onClick={() => approveWithdrawal(item)} disabled={busyId === item.id}>Approve</button>
            <button type="button" className="danger-link" onClick={() => rejectWithdrawal(item)} disabled={busyId === item.id}>Reject</button>
          </div>,
        ])} /> : <Empty text="No tailor withdrawal requests waiting for approval." />}
      </section>

      <section className="section-block">
        <div className="section-head">
          <div>
            <h3>Payment Records</h3>
            <p>Ledger records and gateway/manual verification status.</p>
          </div>
        </div>
        {rows.length ? <Table columns={["Payment", "Order", "Amount", "Method", "Gateway", "Status", "Updated"]} rows={rows.map((r) => [
          r.id,
          r.order_code,
          money(r.amount),
          r.method || "-",
          r.gateway_verified === false || r.verification_status === "unverified_by_gateway" || String(r.method || "").toLowerCase().includes("manual") ? <StatusPill value="MANUAL VERIFICATION" /> : <StatusPill value="GATEWAY VERIFIED" />,
          <StatusPill value={r.status} />,
          fmtDate(r.updated),
        ])} /> : <Empty text="No payment records yet." />}
      </section>
    </div>
  );
}

function Reviews({ rows, reload }) {
  if (!rows.length) return <Empty />;
  return <Table columns={["Customer", "Tailor", "Rating", "Review", "Action"]} rows={rows.map((r) => [
    r.customer_name,
    r.shop,
    `${Number(r.rating).toFixed(1)} star`,
    r.body || "-",
    <button className="danger-link" onClick={async () => { await api.patchReview(r.id, { hidden: !r.hidden, reason: prompt("Reason:") || "Admin moderation" }); reload(); }}>{r.hidden ? "Show" : "Hide"}</button>,
  ])} />;
}

function AdminSupport({ rows, reload }) {
  async function reply(row) {
    const body = prompt(`Reply to ${row.code}:`);
    if (!body) return;
    await api.replySupportTicket(row.id, body);
    reload();
  }

  async function update(row) {
    const status = prompt("Status: OPEN, PENDING, WAITING_ON_CUSTOMER, RESOLVED, CLOSED", row.status) || row.status;
    const priority = prompt("Priority: LOW, NORMAL, HIGH, URGENT", row.priority) || row.priority;
    const note = prompt("Internal note:", "") || "";
    await api.patchSupportTicket(row.id, { status, priority, note });
    reload();
  }

  if (!rows.length) return <Empty text="No support tickets yet." />;
  return <Table columns={["Ticket", "Requester", "Role", "Category", "Priority", "Status", "Latest", "Actions"]} rows={rows.map((r) => [
    <><strong>{r.code}</strong><small>{r.subject}</small></>,
    <><span>{r.requester_name}</span><small>{r.requester_email || r.requester_phone || "-"}</small></>,
    r.requester_role,
    <><span>{r.category}</span><small>{r.order_code || "No order linked"}</small></>,
    <StatusPill value={r.priority} />,
    <StatusPill value={r.status} />,
    fmtDate(r.last_activity_at),
    <div className="inline-actions"><button onClick={() => reply(r)}>Reply</button><button onClick={() => update(r)}>Update</button></div>,
  ])} />;
}

function Complaints({ rows, reload }) {
  if (!rows.length) return <Empty />;
  return <Table columns={["Issue", "Raised By", "Order", "Status", "Resolution", "Actions"]} rows={rows.map((r) => [
    <><strong>{r.subject}</strong><small>{r.body}</small></>,
    r.raiser_name,
    r.order_code || "-",
    <StatusPill value={r.status} />,
    r.resolution || "-",
    <button className="ok-link" onClick={async () => { await api.patchComplaint(r.id, { status: "RESOLVED", resolution: prompt("Resolution:") || "Resolved by admin" }); reload(); }}>Resolve</button>,
  ])} />;
}

function Audit({ rows }) {
  if (!rows.length) return <Empty />;
  return <Table columns={["Time", "Admin", "Action", "Target", "Reason"]} rows={rows.map((r) => [fmtDate(r.ts), r.admin_name, r.action, `${r.target_type || "-"} ${r.target_name || r.target_id || ""}`, r.reason || "-"])} />;
}

function ActionSet({ onActive, onSuspend, onBlock, onDelete }) {
  return <div className="inline-actions"><button onClick={onActive}>Activate</button><button onClick={onSuspend}>Suspend</button><button onClick={onBlock}>Block</button><button className="danger-link" onClick={onDelete}>Delete</button></div>;
}

function Table({ columns, rows, pageSize = DEFAULT_TABLE_PAGE_SIZE, label = "records" }) {
  const pageData = usePagedRows(rows, pageSize);
  return (
    <>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {pageData.rows.map((row, i) => (
              <tr key={`${pageData.start}-${i}`}>
                {row.map((cell, j) => <td key={j}>{cell}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <PaginationControls
        page={pageData.page}
        totalPages={pageData.totalPages}
        total={pageData.total}
        start={pageData.start}
        end={pageData.end}
        onPage={pageData.setPage}
        label={label}
      />
    </>
  );
}

createRoot(document.getElementById("root")).render(<App />);
registerPwa();
