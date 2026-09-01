import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import AlertTriangle from "lucide-react/dist/esm/icons/alert-triangle.js";
import ArrowRight from "lucide-react/dist/esm/icons/arrow-right.js";
import BadgeCheck from "lucide-react/dist/esm/icons/badge-check.js";
import Ban from "lucide-react/dist/esm/icons/ban.js";
import Bell from "lucide-react/dist/esm/icons/bell.js";
import ChevronDown from "lucide-react/dist/esm/icons/chevron-down.js";
import ChevronLeft from "lucide-react/dist/esm/icons/chevron-left.js";
import CheckCircle2 from "lucide-react/dist/esm/icons/check-circle-2.js";
import ClipboardList from "lucide-react/dist/esm/icons/clipboard-list.js";
import Crown from "lucide-react/dist/esm/icons/crown.js";
import CreditCard from "lucide-react/dist/esm/icons/credit-card.js";
import FileClock from "lucide-react/dist/esm/icons/file-clock.js";
import Globe2 from "lucide-react/dist/esm/icons/globe-2.js";
import Heart from "lucide-react/dist/esm/icons/heart.js";
import Eye from "lucide-react/dist/esm/icons/eye.js";
import EyeOff from "lucide-react/dist/esm/icons/eye-off.js";
import ImageIcon from "lucide-react/dist/esm/icons/image.js";
import LayoutDashboard from "lucide-react/dist/esm/icons/layout-dashboard.js";
import LogOut from "lucide-react/dist/esm/icons/log-out.js";
import Megaphone from "lucide-react/dist/esm/icons/megaphone.js";
import Menu from "lucide-react/dist/esm/icons/menu.js";
import Moon from "lucide-react/dist/esm/icons/moon.js";
import Pencil from "lucide-react/dist/esm/icons/pencil.js";
import RefreshCw from "lucide-react/dist/esm/icons/refresh-cw.js";
import Scissors from "lucide-react/dist/esm/icons/scissors.js";
import Search from "lucide-react/dist/esm/icons/search.js";
import Shield from "lucide-react/dist/esm/icons/shield.js";
import SlidersHorizontal from "lucide-react/dist/esm/icons/sliders-horizontal.js";
import Star from "lucide-react/dist/esm/icons/star.js";
import MapPin from "lucide-react/dist/esm/icons/map-pin.js";
import Sun from "lucide-react/dist/esm/icons/sun.js";
import Tag from "lucide-react/dist/esm/icons/tag.js";
import Trash2 from "lucide-react/dist/esm/icons/trash-2.js";
import UploadCloud from "lucide-react/dist/esm/icons/upload-cloud.js";
import UsersRound from "lucide-react/dist/esm/icons/users-round.js";
import Video from "lucide-react/dist/esm/icons/video.js";
import XCircle from "lucide-react/dist/esm/icons/x-circle.js";
import { api, assetUrl, clearSession, getRefreshToken, getRole, getToken, hasValidStoredSession, INACTIVITY_LOGOUT_MESSAGE, isSessionExpired, isSessionInactive, markSessionActive, setSession } from "./api";
import { registerPwa } from "./registerPwa";
import "./styles.css";
import "./premium-ui.css";

const MapPicker = React.lazy(() => import("./components/MapPicker"));

function LazyMapPicker(props) {
  return (
    <React.Suspense fallback={<div className="loading">Loading map...</div>}>
      <MapPicker {...props} />
    </React.Suspense>
  );
}

const publicRoles = [
  ["customer", "Customer", UsersRound, "Find tailors, book and track orders."],
  ["tailor", "Tailor", Scissors, "Manage bookings, services and earnings."],
];
const adminRole = ["admin", "Admin", Shield, "Review and manage platform operations."];
const roles = [...publicRoles, adminRole];

function isAdminPortalPath(pathname = window.location.pathname) {
  return /^\/admin(?:\/|$)/i.test(pathname);
}

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
    "home.premiumBadge": "టైలరింగ్‌కు కొత్త మెరుగుదల",
    "home.kicker": "ఆలోచించి కుట్టిన ఫిట్. ఆత్మవిశ్వాసంతో మీరు.",
    "home.heroLead": "మీ కోసం",
    "home.heroEmphasis": "ప్రత్యేకంగా",
    "home.heroTail": "రూపొందించబడింది.",
    "home.description": "ధృవీకరించిన టైలరింగ్ నిపుణులను ఎంచుకుని, ప్రతి వివరాన్ని నిర్ణయించి, కొలతల నుంచి తుది ఫిట్టింగ్ వరకు మీ ఆర్డర్‌ను అనుసరించండి.",
    "home.welcome": "TailoraHub‌కు స్వాగతం",
    "home.continueTitle": "మీరు ఎలా కొనసాగాలనుకుంటున్నారు?",
    "home.benefitsLabel": "TailoraHub ప్రయోజనాలు",
    "home.footerTagline": "నమ్మకం, నైపుణ్యం మరియు సరైన ఫిట్ చుట్టూ రూపుదిద్దుకుంది.",
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
const ROUTE_QUERY_KEYS = {
  authStage: "auth",
  customerPanel: "view",
  customerTailorId: "tailorId",
  tailorPanel: "view",
  adminSection: "view",
};
const ROLE_DEFAULT_VIEWS = { customer: "overview", tailor: "overview", admin: "dashboard" };
const ROLE_VIEWS = {
  customer: new Set(["overview", "browse", "profile", "account", "account-profile", "favorites", "updates", "wallet", "referrals", "requests", "orders", "support"]),
  tailor: new Set(["overview", "profile", "availability", "wallet", "referrals", "media", "services", "offers", "followers", "requests", "waiting", "orders", "updates", "support"]),
  admin: new Set(adminSections.map(([id]) => id)),
};

function clearNavigationState() {
  Object.keys(sessionStorage).forEach((key) => {
    if (key.startsWith(`${APP_HISTORY_KEY}:view:`)) sessionStorage.removeItem(key);
  });
}

function roleFromAuthenticatedUser(storedRole, user) {
  const roles = Array.isArray(user?.roles) ? user.roles.map((value) => String(value).toLowerCase()) : [];
  if (roles.includes(storedRole)) return storedRole;
  return ["admin", "tailor", "customer"].find((candidate) => roles.includes(candidate)) || "";
}

function replaceWithRoleLanding(roleName) {
  const defaultView = ROLE_DEFAULT_VIEWS[roleName];
  const url = new URL(window.location.href);
  url.pathname = roleName === "admin" ? "/admin" : "/";
  url.search = "";
  url.hash = "";
  if (defaultView) url.searchParams.set("view", defaultView);
  window.history.replaceState({ [APP_HISTORY_KEY]: {} }, "", `${url.pathname}${url.search}`);
}

function validateRestoredRoute(roleName) {
  const allowedViews = ROLE_VIEWS[roleName];
  const defaultView = ROLE_DEFAULT_VIEWS[roleName];
  if (!allowedViews || !defaultView) return;
  const url = new URL(window.location.href);
  let requestedView = url.searchParams.get("view");
  if (roleName === "customer" && requestedView === "account-profile") {
    requestedView = "account";
    url.searchParams.set("view", requestedView);
    window.history.replaceState(currentHistoryState(), "", `${url.pathname}${url.search}${url.hash}`);
  }
  const validProfile = roleName !== "customer" || requestedView !== "profile" || Boolean(url.searchParams.get("tailorId"));
  if (requestedView && allowedViews.has(requestedView) && validProfile) return;
  url.searchParams.set("view", defaultView);
  url.searchParams.delete("tailorId");
  window.history.replaceState(currentHistoryState(), "", `${url.pathname}${url.search}${url.hash}`);
}
const MEASUREMENT_APPOINTMENT_ERROR = "Measurement appointment must be on or before the delivery date.";
const APPOINTMENT_TIME_SLOTS = [
  { value: "08:00-10:00", label: "8:00 AM-10:00 AM", startMinutes: 480 },
  { value: "10:00-12:00", label: "10:00 AM-12:00 PM", startMinutes: 600 },
  { value: "12:00-14:00", label: "12:00 PM-2:00 PM", startMinutes: 720 },
  { value: "14:00-16:00", label: "2:00 PM-4:00 PM", startMinutes: 840 },
  { value: "16:00-18:00", label: "4:00 PM-6:00 PM", startMinutes: 960 },
  { value: "18:00-20:00", label: "6:00 PM-8:00 PM", startMinutes: 1080 },
  { value: "20:00-22:00", label: "8:00 PM-10:00 PM", startMinutes: 1200 },
];

function currentHistoryState() {
  const state = window.history.state;
  return state && typeof state === "object" ? state : {};
}

function readAppHistoryValue(scope, fallback) {
  const queryKey = ROUTE_QUERY_KEYS[scope];
  if (queryKey) {
    const routeValue = new URLSearchParams(window.location.search).get(queryKey);
    if (routeValue !== null) return routeValue;
  }
  const appState = currentHistoryState()[APP_HISTORY_KEY];
  if (appState && Object.prototype.hasOwnProperty.call(appState, scope)) return appState[scope];
  try {
    const stored = window.sessionStorage.getItem(`${APP_HISTORY_KEY}:view:${scope}`);
    return stored === null ? fallback : JSON.parse(stored);
  } catch {
    return fallback;
  }
}

function ExpiryCountdown({ expiresAt }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!expiresAt) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [expiresAt]);
  if (!expiresAt) return null;
  const remaining = Math.max(0, new Date(expiresAt).getTime() - now);
  const minutes = Math.floor(remaining / 60000);
  const seconds = Math.floor((remaining % 60000) / 1000);
  return <small className={remaining ? "countdown" : "field-error"}>{remaining ? `Tailor response time: ${minutes}:${String(seconds).padStart(2, "0")}` : "Tailor response time expired"}</small>;
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
  const url = new URL(window.location.href);
  const queryKey = ROUTE_QUERY_KEYS[scope];
  if (queryKey) {
    if (value === "" || value === null || value === undefined) url.searchParams.delete(queryKey);
    else url.searchParams.set(queryKey, String(value));
  }
  window.history[method](next, "", `${url.pathname}${url.search}${url.hash}`);
  try {
    window.sessionStorage.setItem(`${APP_HISTORY_KEY}:view:${scope}`, JSON.stringify(value));
  } catch {
    // History state still works when browser storage is unavailable.
  }
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
      try {
        window.sessionStorage.setItem(`${APP_HISTORY_KEY}:view:${scope}`, JSON.stringify(next));
      } catch {
        // Ignore unavailable browser storage.
      }
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

function useAutoRefresh(refresh) {
  const refreshRef = useRef(refresh);
  const runningRef = useRef(false);
  useEffect(() => { refreshRef.current = refresh; }, [refresh]);
  useEffect(() => {
    async function run() {
      if (runningRef.current || document.visibilityState === "hidden") return;
      runningRef.current = true;
      try {
        await refreshRef.current();
      } finally {
        runningRef.current = false;
      }
    }
    function handleVisible() {
      if (document.visibilityState === "visible") run();
    }
    window.addEventListener("focus", run);
    window.addEventListener("online", run);
    window.addEventListener("tailorahub:data-changed", run);
    document.addEventListener("visibilitychange", handleVisible);
    return () => {
      window.removeEventListener("focus", run);
      window.removeEventListener("online", run);
      window.removeEventListener("tailorahub:data-changed", run);
      document.removeEventListener("visibilitychange", handleVisible);
    };
  }, []);
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
  return deliveryDate || "";
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

function LogoutConfirmDialog({ open, onCancel, onConfirm }) {
  const cancelButtonRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    cancelButtonRef.current?.focus();
    function handleKeyDown(event) {
      if (event.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) return null;
  return (
    <div className="th-confirm-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel(); }}>
      <section className="th-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="logout-dialog-title" aria-describedby="logout-dialog-description">
        <div className="th-confirm-icon" aria-hidden="true"><LogOut size={20} /></div>
        <div className="th-confirm-copy">
          <h2 id="logout-dialog-title">Log out of TailoraHub?</h2>
          <p id="logout-dialog-description">You will need to sign in again to access your workspace.</p>
        </div>
        <div className="th-confirm-actions">
          <button ref={cancelButtonRef} type="button" className="secondary-btn" onClick={onCancel}>Cancel</button>
          <button type="button" className="primary-btn" onClick={onConfirm}>Log out</button>
        </div>
      </section>
    </div>
  );
}

function ExternalPaymentConfirmDialog({ open, onCancel, onConfirm, busy = false }) {
  const cancelButtonRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    cancelButtonRef.current?.focus();
    function handleKeyDown(event) {
      if (event.key === "Escape" && !busy) onCancel();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel, busy]);
  if (!open) return null;
  return (
    <div className="th-confirm-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onCancel(); }}>
      <section className="th-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="payment-dialog-title" aria-describedby="payment-dialog-description">
        <div className="th-confirm-icon payment-confirm-icon" aria-hidden="true"><CreditCard size={20} /></div>
        <div className="th-confirm-copy">
          <h2 id="payment-dialog-title">Continue to secure payment?</h2>
          <p id="payment-dialog-description">You are about to continue to Razorpay, our secure payment partner, to complete this booking payment.</p>
        </div>
        <div className="th-confirm-actions">
          <button ref={cancelButtonRef} type="button" className="secondary-btn" onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="button" className="primary-btn" onClick={onConfirm} disabled={busy}>{busy ? "Opening..." : "Proceed to payment"}</button>
        </div>
      </section>
    </div>
  );
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
            <img src={item.url} alt={item.name} loading="lazy" decoding="async" />
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
  const adminPortal = isAdminPortalPath();
  const [referralEntry, setReferralEntry] = useState(() => readReferralEntry());
  const [role, setRole] = useState("");
  const [signedIn, setSignedIn] = useState(false);
  const [authInitializing, setAuthInitializing] = useState(true);
  const [authNotice, setAuthNotice] = useState("");
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false);
  const [theme, setTheme] = useState(initialTheme);
  const [language, setLanguage] = useState(initialLanguage);
  const languageValue = useMemo(() => ({
    language,
    setLanguage,
    t: (key, fallback, values) => translate(language, key, fallback, values),
  }), [language]);

  useEffect(() => {
    if (!signedIn) setLogoutConfirmOpen(false);
  }, [signedIn]);

  useEffect(() => {
    function handleSessionCleared(event) {
      setSignedIn(false);
      setRole("");
      if (event.detail?.reason) setAuthNotice(event.detail.reason);
    }
    window.addEventListener("tailorahub:session-cleared", handleSessionCleared);
    return () => window.removeEventListener("tailorahub:session-cleared", handleSessionCleared);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function restoreAuthentication() {
      if (referralEntry || !hasValidStoredSession()) {
        if (!cancelled) setAuthInitializing(false);
        return;
      }
      try {
        const me = await api.me();
        const restoredRole = roleFromAuthenticatedUser(getRole(), me?.user);
        if (!restoredRole) throw new Error("Authenticated account has no supported role");
        if ((restoredRole === "admin") !== adminPortal) {
          throw new Error("This session belongs to a different TailoraHub portal");
        }
        if (!cancelled) {
          validateRestoredRoute(restoredRole);
          setRole(restoredRole);
          setSignedIn(true);
        }
      } catch {
        clearSession();
      } finally {
        if (!cancelled) setAuthInitializing(false);
      }
    }
    restoreAuthentication();
    return () => { cancelled = true; };
  }, [adminPortal, referralEntry]);

  useEffect(() => {
    if (!referralEntry) return;
    clearSession();
    setSignedIn(false);
    setRole("");
  }, [referralEntry]);

  useEffect(() => {
    if (!signedIn) return undefined;

    function expireIfIdle() {
      const inactive = isSessionInactive();
      if (!inactive && (!isSessionExpired() || getRefreshToken())) return false;
      const reason = inactive ? INACTIVITY_LOGOUT_MESSAGE : "Session expired. Please log in again.";
      const refresh = getRefreshToken();
      if (refresh) api.logoutSession(refresh).catch(() => {});
      clearSession(reason);
      setSignedIn(false);
      setRole("");
      return true;
    }

    function handleActivity() {
      if (!expireIfIdle()) markSessionActive();
    }

    function handleResume() {
      if (document.visibilityState === "hidden") return;
      expireIfIdle();
    }

    const activityEvents = ["click", "keydown", "input", "pointerdown", "touchstart", "scroll", "popstate"];
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

  useEffect(() => {
    document.title = adminPortal ? "TailoraHub Private Admin" : "TailoraHub";
    let robots = document.querySelector('meta[name="robots"]');
    if (!robots) {
      robots = document.createElement("meta");
      robots.name = "robots";
      document.head.appendChild(robots);
    }
    robots.content = adminPortal ? "noindex, nofollow, noarchive" : "index, follow";
  }, [adminPortal]);

  function handleAuth(res, selectedRole) {
    const nextRole = res.role || selectedRole;
    if ((nextRole === "admin") !== adminPortal) {
      clearSession();
      setAuthNotice(adminPortal ? "Only an administrator can use this private portal." : "Administrator access is available only through the private admin portal.");
      return;
    }
    clearNavigationState();
    replaceWithRoleLanding(nextRole);
    setSession(res.token || res.access_token, nextRole, res.refreshToken || res.refresh_token);
    setAuthNotice("");
    setRole(nextRole);
    setSignedIn(true);
    if (referralEntry) {
      clearReferralBrowserUrl();
      setReferralEntry(null);
    }
  }

  function requestLogout() {
    setLogoutConfirmOpen(true);
  }

  async function logout() {
    setLogoutConfirmOpen(false);
    const refresh = getRefreshToken();
    if (refresh) await api.logoutSession(refresh).catch(() => {});
    clearSession();
    clearNavigationState();
    window.history.replaceState({}, "", adminPortal ? "/admin" : "/");
    setSignedIn(false);
    setRole("");
  }

  let content;
  if (authInitializing) content = <main className="app-shell"><section className="panel"><p>Restoring your secure session...</p></section></main>;
  else if (!signedIn) content = <AuthShell onAuth={handleAuth} theme={theme} setTheme={setTheme} language={language} setLanguage={setLanguage} referralEntry={referralEntry} sessionMessage={authNotice} adminPortal={adminPortal} />;
  else if (!adminPortal && role === "customer") content = <CustomerApp onLogout={requestLogout} />;
  else if (!adminPortal && role === "tailor") content = <TailorApp onLogout={requestLogout} />;
  else if (adminPortal && role === "admin") content = <AdminApp onLogout={requestLogout} />;
  else content = <AuthShell onAuth={handleAuth} theme={theme} setTheme={setTheme} language={language} setLanguage={setLanguage} referralEntry={null} sessionMessage="Use the correct TailoraHub portal for this account." adminPortal={adminPortal} />;

  return (
    <LanguageContext.Provider value={languageValue}>
      {content}
      <LogoutConfirmDialog open={logoutConfirmOpen} onCancel={() => setLogoutConfirmOpen(false)} onConfirm={logout} />
    </LanguageContext.Provider>
  );
}

const tailorWizardSteps = [
  "Mobile",
  "Email",
  "Aadhaar",
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

function customerIdentifierError(value) {
  const identifier = String(value || "").trim();
  if (!identifier) return "Enter your mobile number or email";
  if (identifier.includes("@")) return isValidEmail(identifier) ? "" : "Enter a valid email address, for example name@example.com";
  return isValidIndianPhone(identifier) ? "" : "Enter a valid email address or 10-digit mobile number";
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

function AuthShell({ onAuth, theme, setTheme, language, setLanguage, referralEntry, sessionMessage = "", adminPortal = false }) {
  const t = useT();
  const [authStage, setAuthStage] = useAppHistoryState("authStage", adminPortal ? "auth" : "home");
  const [selectedRole, setSelectedRole] = useState(adminPortal ? "admin" : "customer");
  const [mode, setMode] = useState("login");
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
  const [forgotFlow, setForgotFlow] = useState({
    active: false,
    step: "request",
    identifier: "",
    channel: "email",
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
    setForgotFlow({ active: false, step: "request", identifier: "", channel: "email", otp: "", newPassword: "", confirmPassword: "", target: "", cooldown: 0 });
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
    if (!forgotFlow.cooldown) return undefined;
    const timer = setInterval(() => {
      setForgotFlow((old) => ({ ...old, cooldown: Math.max(0, old.cooldown - 1) }));
    }, 1000);
    return () => clearInterval(timer);
  }, [forgotFlow.cooldown]);

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
    if (key === "aadhaarNumber") return !value ? "" : isValidAadhaar(value) ? "" : "Enter a valid Aadhaar number";
    if (key === "name") return value.trim().length >= 2 ? "" : "Enter your full name";
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
        const res = selectedRole === "admin"
          ? await api.adminLogin(form.identifier, form.password)
          : await api.login(selectedRole, form.identifier, form.password);
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
          aadhaar_number: cleanDigits(form.aadhaarNumber) || undefined,
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
    if (!form.identifier.trim()) throw new Error("Enter your username, mobile number or email");
    if (!form.password) throw new Error("Enter your password");
    const res = await api.tailorV1Login({ identifier: form.identifier, mode: "password", password: form.password });
    onAuth(res, "tailor");
  }

  async function submitCustomerLogin() {
    const identifierError = customerIdentifierError(form.identifier);
    if (identifierError) throw new Error(identifierError);
    if (!form.password) throw new Error("Enter your password");
    const res = await api.customerV1Login({ identifier: form.identifier, mode: "password", password: form.password });
    onAuth(res, "customer");
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
      channel: "email",
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
    setForgotFlow({ active: false, step: "request", identifier: "", channel: "email", otp: "", newPassword: "", confirmPassword: "", target: "", cooldown: 0 });
  }

  async function sendForgotPasswordOtp() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      if (!forgotFlow.identifier.trim()) throw new Error(selectedRole === "customer" ? "Enter your mobile number or email" : "Enter your username, mobile number or email");
      if (selectedRole === "customer") {
        const identifierError = customerIdentifierError(forgotFlow.identifier);
        if (identifierError) throw new Error(identifierError);
      }
      const res = selectedRole === "customer"
        ? await api.customerForgotPassword(forgotFlow.identifier, forgotFlow.channel)
        : await api.tailorForgotPassword(forgotFlow.identifier, forgotFlow.channel);
      setForgotFlow((old) => ({ ...old, step: "reset", target: res.target || "", cooldown: 30 }));
      setInfo(`Reset OTP sent to ${res.target || "your registered contact"}.`);
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
        channel: forgotFlow.channel,
        otp: forgotFlow.otp,
        new_password: forgotFlow.newPassword,
        confirm_password: forgotFlow.confirmPassword,
      };
      if (selectedRole === "customer") await api.customerResetPassword(payload);
      else await api.tailorResetPassword(payload);
      update("identifier", forgotFlow.identifier);
      update("password", "");
      closeForgotPassword();
      setInfo("Password updated. You can now sign in.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // Registration-time phone/email verification uses separate purpose-scoped OTPs
  // and must complete before either a customer or tailor account is created.
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
      setOtpState((old) => ({
        ...old,
        [`${kind}Sent`]: true,
        [`${kind}Cooldown`]: 30,
      }));
      setInfo(`Verification code sent to your ${kind === "phone" ? "mobile number" : "email"}.`);
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
    if (!isValidEmail(form.email)) return "Enter a valid email address";
    if (fieldErrors.email) return fieldErrors.email;
    if (!otpState.emailVerified) return "Verify your email address";
    if (!form.confirmPassword) return "Confirm your password";
    if (passwordMessage(form.password, form.confirmPassword)) return passwordMessage(form.password, form.confirmPassword);
    if (!form.termsAccepted) return "Accept the terms and conditions";
    return "";
  }

  function stepError(index) {
    if (index === 0) {
      if (!isValidIndianPhone(form.phone)) return "Enter a valid 10-digit mobile number";
      if (fieldErrors.phone) return fieldErrors.phone;
      if (!otpState.phoneVerified) return "Verify your mobile number";
    }
    if (index === 1) {
      if (!isValidEmail(form.email)) return "Enter a valid email address";
      if (fieldErrors.email) return fieldErrors.email;
      if (!otpState.emailVerified) return "Verify your email";
    }
    if (index === 2) {
      const aadhaar = cleanDigits(form.aadhaarNumber);
      if (!form.name.trim()) return "Enter your full name";
      if (!form.dob) return "Enter your date of birth";
      if (fieldErrors.name || fieldErrors.dob) return fieldErrors.name || fieldErrors.dob;
      if (aadhaar && !isValidAadhaar(aadhaar)) return "Enter a valid 12-digit Aadhaar number or leave it blank";
      if (fieldErrors.aadhaarNumber) return fieldErrors.aadhaarNumber;
      if (aadhaar && !aadhaarVerified) return "Verify Aadhaar or leave it blank for now";
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
  const authRoles = adminPortal
    ? [adminRole]
    : referralLockedRole
      ? publicRoles.filter(([id]) => id === referralLockedRole)
      : publicRoles;
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
    setForgotFlow({ active: false, step: "request", identifier: "", channel: "email", otp: "", newPassword: "", confirmPassword: "", target: "", cooldown: 0 });
  }

  function renderTailorLogin() {
    if (forgotFlow.active) return renderForgotPassword();
    return (
      <div className="tailor-login-panel">
        <Field label={t("auth.usernameMobileOrEmail", "Username, mobile number or email")}>
          <input value={form.identifier} onChange={(e) => update("identifier", e.target.value)} autoComplete="username" placeholder="username, 10 digit mobile or email" />
        </Field>
        <Field label={t("common.password", "Password")}>
          <PasswordInput value={form.password} onChange={(e) => update("password", e.target.value)} autoComplete="current-password" />
        </Field>
        <button type="button" className="text-link" onClick={openForgotPassword}>{t("auth.forgotPassword", "Forgot password?")}</button>
      </div>
    );
  }

  function renderCustomerLogin() {
    if (forgotFlow.active) return renderForgotPassword();
    const identifierError = form.identifier.trim() ? customerIdentifierError(form.identifier) : "";
    return (
      <div className="tailor-login-panel">
        <Field label={t("auth.mobileOrEmail", "Mobile number or email")} error={identifierError}>
          <input value={form.identifier} onChange={(e) => update("identifier", e.target.value)} autoComplete="username" placeholder="10 digit mobile or email" />
        </Field>
        <Field label={t("common.password", "Password")}>
          <PasswordInput value={form.password} onChange={(e) => update("password", e.target.value)} autoComplete="current-password" />
        </Field>
        <button type="button" className="text-link" onClick={openForgotPassword}>{t("auth.forgotPassword", "Forgot password?")}</button>
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
            <label className="field-label">Send reset code to</label>
            <div className="segmented login-mode-toggle" role="group" aria-label="Reset code delivery method">
              <button type="button" className={forgotFlow.channel === "email" ? "active" : ""} onClick={() => setForgotFlow((old) => ({ ...old, channel: "email" }))}>Email</button>
              <button type="button" className={forgotFlow.channel === "sms" ? "active" : ""} onClick={() => setForgotFlow((old) => ({ ...old, channel: "sms" }))}>Mobile SMS</button>
            </div>
            <Field label={isCustomer ? t("auth.mobileOrEmail", "Mobile number or email") : t("auth.usernameMobileOrEmail", "Username, mobile number or email")}>
              <input value={forgotFlow.identifier} onChange={(e) => setForgotFlow((old) => ({ ...old, identifier: e.target.value }))} autoComplete="username" placeholder={forgotFlow.channel === "email" ? "Enter registered email" : "Enter registered mobile number"} />
            </Field>
            <button type="button" className="primary-btn" onClick={sendForgotPasswordOtp} disabled={busy}>{busy ? t("common.pleaseWait", "Please wait...") : t("auth.sendResetOtp", "Send reset OTP")}</button>
          </>
        ) : (
          <>
            <Field label={t("auth.otpCode", "OTP code")}>
              <input value={forgotFlow.otp} onChange={(e) => setForgotFlow((old) => ({ ...old, otp: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} />
            </Field>
            <Field label={t("auth.newPassword", "New password")} error={forgotFlow.newPassword ? resetPasswordError : ""}>
              <PasswordInput ariaLabel="New password" value={forgotFlow.newPassword} onChange={(e) => setForgotFlow((old) => ({ ...old, newPassword: e.target.value }))} autoComplete="new-password" />
            </Field>
            <Field label={t("auth.confirmNewPassword", "Confirm new password")} error={forgotFlow.confirmPassword && resetPasswordError ? resetPasswordError : ""}>
              <PasswordInput ariaLabel="Confirm new password" value={forgotFlow.confirmPassword} onChange={(e) => setForgotFlow((old) => ({ ...old, confirmPassword: e.target.value }))} autoComplete="new-password" />
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
          <Field label={t("auth.emailRequired", "Email address (required)")} error={fieldErrors.email} success={otpState.emailVerified ? "Email verified" : fieldSuccess.email || (checking.email ? "Checking..." : "")}>
            <input value={form.email} onChange={(e) => update("email", e.target.value)} onBlur={() => checkAvailability("email", form.email)} type="email" autoComplete="email" placeholder="Enter your email address" />
          </Field>
          <Field label={t("auth.sixDigitOtp", "6 digit OTP")} error={otpState.emailSent && !otpState.emailVerified && !otpState.emailCode ? "Enter the OTP sent to email" : ""}>
            <input value={otpState.emailCode} onChange={(e) => setOtpState((old) => ({ ...old, emailCode: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} disabled={otpState.emailVerified} />
          </Field>
          <div className="span-2 inline-actions">
            <button type="button" className="secondary-btn" onClick={() => sendRegistrationOtp("email")} disabled={busy || otpState.emailVerified || otpState.emailCooldown > 0}>{otpState.emailCooldown > 0 ? `Resend in ${otpState.emailCooldown}s` : otpState.emailSent ? "Resend OTP" : "Send email OTP"}</button>
            <button type="button" className="ok-btn" onClick={() => verifyRegistrationOtp("email")} disabled={busy || otpState.emailVerified || !otpState.emailSent}>Verify email</button>
          </div>
          <Field label={t("auth.mobileNumber", "Mobile number")} error={fieldErrors.phone} success={otpState.phoneVerified ? "Mobile number verified" : fieldSuccess.phone || (checking.phone ? "Checking..." : "")}>
            <input value={form.phone} onChange={(e) => update("phone", e.target.value)} onBlur={() => checkAvailability("phone", form.phone)} type="tel" inputMode="numeric" maxLength={10} autoComplete="tel" placeholder="Enter 10 digit mobile number" />
          </Field>
          <Field label={t("auth.sixDigitOtp", "6 digit OTP")} error={otpState.phoneSent && !otpState.phoneVerified && !otpState.phoneCode ? "Enter the OTP sent to mobile" : ""}>
            <input value={otpState.phoneCode} onChange={(e) => setOtpState((old) => ({ ...old, phoneCode: cleanDigits(e.target.value) }))} inputMode="numeric" maxLength={6} disabled={otpState.phoneVerified} />
          </Field>
          <div className="span-2 inline-actions">
            <button type="button" className="secondary-btn" onClick={() => sendRegistrationOtp("phone")} disabled={busy || otpState.phoneVerified || otpState.phoneCooldown > 0}>{otpState.phoneCooldown > 0 ? `Resend in ${otpState.phoneCooldown}s` : otpState.phoneSent ? "Resend OTP" : "Send mobile OTP"}</button>
            <button type="button" className="ok-btn" onClick={() => verifyRegistrationOtp("phone")} disabled={busy || otpState.phoneVerified || !otpState.phoneSent}>Verify mobile</button>
          </div>
          <Field label={t("common.password", "Password")} error={fieldErrors.password}>
            <PasswordInput value={form.password} onChange={(e) => update("password", e.target.value)} autoComplete="new-password" />
          </Field>
          <Field label={t("auth.confirmPassword", "Confirm password")} error={fieldErrors.confirmPassword}>
            <PasswordInput ariaLabel="Confirm password" value={form.confirmPassword} onChange={(e) => update("confirmPassword", e.target.value)} autoComplete="new-password" />
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
    if (wizardStep === 2) {
      return (
        <div className="wizard-grid">
          <Field label="Aadhaar number (optional for now)" error={fieldErrors.aadhaarNumber} hint="You can leave this blank and complete verification later." success={fieldSuccess.aadhaarNumber || (checking.aadhaarNumber ? "Checking..." : "")}>
            <input value={form.aadhaarNumber} onChange={(e) => update("aadhaarNumber", e.target.value)} onBlur={() => checkAvailability("aadhaar", form.aadhaarNumber)} inputMode="numeric" maxLength={12} placeholder="12 digits (optional)" readOnly={aadhaarVerified} />
          </Field>
          <Field label="Full name" error={fieldErrors.name} hint={form.aadhaarNumber ? "Must match Aadhaar name when provided" : "Enter your legal name"}>
            <input value={form.name} onChange={(e) => update("name", e.target.value)} readOnly={aadhaarVerified} />
          </Field>
          <Field label="Date of birth" error={fieldErrors.dob}>
            <input value={form.dob} onChange={(e) => update("dob", e.target.value)} type="date" readOnly={aadhaarVerified} />
          </Field>
          <div className="span-2 inline-actions">
            <button type="button" className="secondary-btn" onClick={verifyAadhaar} disabled={busy || aadhaarVerified || !isValidAadhaar(form.aadhaarNumber)}>{aadhaarVerified ? "Aadhaar Verified" : "Verify eKYC (optional)"}</button>
          </div>
        </div>
      );
    }
    if (wizardStep === 0) {
      return (
        <div className="wizard-grid">
          <Field label="Mobile number" error={fieldErrors.phone} success={otpState.phoneVerified ? "Mobile number verified" : fieldSuccess.phone || (checking.phone ? "Checking..." : "")}>
            <input value={form.phone} onChange={(e) => update("phone", e.target.value)} onBlur={() => checkAvailability("phone", form.phone)} type="tel" inputMode="numeric" maxLength={10} autoComplete="tel" placeholder="Enter 10 digit mobile number" />
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
    if (wizardStep === 1) {
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
            <PasswordInput value={form.password} onChange={(e) => update("password", e.target.value)} autoComplete="new-password" />
          </Field>
          <Field label="Confirm password" error={fieldErrors.confirmPassword}>
            <PasswordInput ariaLabel="Confirm password" value={form.confirmPassword} onChange={(e) => update("confirmPassword", e.target.value)} autoComplete="new-password" />
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
          <LazyMapPicker
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

  if (authStage === "home" && !adminPortal) {
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

          <div className="home-experience">
            <div className="home-editorial-copy">
              <span className="home-premium-badge"><Star size={13} /> {t("home.premiumBadge", "Tailoring, elevated")}</span>
              <p className="home-kicker">{t("home.kicker", "A considered fit. A confident you.")}</p>
              <h1>{t("home.heroLead", "Crafted for")} <em>{t("home.heroEmphasis", "your")}</em> {t("home.heroTail", "story.")}</h1>
              <p className="home-description">
                {t("home.description", "Meet verified tailoring professionals, shape every detail and follow your order from first measurement to final fitting.")}
              </p>
              <div className="home-proof" aria-label={t("home.benefitsLabel", "TailoraHub benefits")}>
                <span><BadgeCheck size={18} /> {t("home.verifiedTailors", "Verified ateliers")}</span>
                <span><CreditCard size={18} /> {t("home.securePayments", "Secure payments")}</span>
                <span><Star size={18} /> {t("home.premiumExperience", "Quality assured")}</span>
              </div>
            </div>

            <section className="home-role-panel" aria-labelledby="role-selection-title">
              <div className="home-role-heading">
                <div>
                  <span>{t("home.welcome", "Welcome to TailoraHub")}</span>
                  <h2 id="role-selection-title">{t("home.continueTitle", "How would you like to continue?")}</h2>
                </div>
                <small>{t("home.chooseRole", "Choose your space")}</small>
              </div>
              <div className="role-grid luxury-role-grid" aria-label={t("home.chooseRole", "Choose role")}>
                {publicRoles.map((role) => (
                  <LuxuryRoleCard key={role[0]} role={role} active={selectedRole === role[0]} onSelect={chooseRole} />
                ))}
              </div>
            </section>
          </div>

          <footer className="home-footer"><span>© 2026 TailoraHub</span><span>{t("home.footerTagline", "Designed around trust, craft and fit.")}</span></footer>
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
            <span><b>{adminPortal ? "Private" : "2"}</b> {adminPortal ? "access" : t("common.roles", "roles")}</span>
            <span><b>Live</b> {t("common.orders", "orders")}</span>
            <span><b>OTP</b> secured</span>
          </div>
        </div>
        <div className="auth-form-panel">
          <div className="auth-back-row">
            {adminPortal ? (
              <span className="referral-lock-note"><Shield size={15} /> Private administrator portal</span>
            ) : referralLockedRole ? (
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
          {!adminPortal ? (
            <div className="role-grid compact-role-grid">
              {authRoles.map((role) => (
                <LuxuryRoleCard key={role[0]} role={role} active={selectedRole === role[0]} onSelect={(roleId) => {
                  if (referralLockedRole) return;
                  setSelectedRole(roleId);
                  setMode("login");
                }} />
              ))}
            </div>
          ) : null}
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
                <PasswordInput value={form.password} onChange={(e) => update("password", e.target.value)} autoComplete="current-password" />
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
              {busy ? t("common.pleaseWait", "Please wait...") : mode === "login" ? t("auth.loginAs", `Login as ${selectedRole}`, { role: selectedRoleLabel }) : t("auth.createAccount", `Create ${selectedRole} account`, { role: selectedRoleLabel })}
            </button>
          ) : null}
          </form>
        </div>
      </section>
    </main>
  );
}

function Shell({ title, subtitle, icon: Icon, onLogout, children, actions, variant = "default", searchValue = "", onSearch, onUpdates, avatarLabel = "TH", unread = 0, mobileTitle = "Overview", onMobileMenu, mobileMenuOpen = false }) {
  const { language, setLanguage, t } = useLanguage();
  if (variant === "customer" || variant === "tailor") {
    const workspaceName = variant === "tailor" ? "Tailor workspace" : "Customer workspace";
    return (
      <div className={`page-shell customer-page-shell ${variant}-page-shell`}>
        <header className="customer-global-header">
          <button type="button" className="workspace-mobile-back" onClick={() => window.history.back()} aria-label="Go back"><ChevronLeft size={20} /></button>
          <div className="customer-preview-label" aria-label="TailoraHub customer workspace">
            <Scissors size={18} />
            <span><strong>{workspaceName}</strong><small>Live account and booking data</small></span>
          </div>
          <label className="customer-global-search">
            <Search size={19} />
            <input
              value={searchValue}
              onChange={(event) => onSearch?.(event.target.value)}
              placeholder="Search this workspace"
              aria-label="Search this workspace"
            />
            <kbd>Ctrl K</kbd>
          </label>
          <button type="button" className="workspace-mobile-current" onClick={onMobileMenu} aria-label="Open workspace navigation" aria-expanded={mobileMenuOpen}>
            <Menu size={19} />
            <span>{mobileTitle}</span>
            <ChevronDown size={17} />
          </button>
          <div className="customer-global-actions">
            <button type="button" className="customer-bell-btn" onClick={onUpdates} aria-label="Open updates">
              <Bell size={18} />
              {unread ? <b>{unread}</b> : null}
            </button>
            <span className="customer-top-avatar" aria-label={title}>{avatarLabel}</span>
          </div>
        </header>
        {children}
      </div>
    );
  }
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

/* APPROVED_PREVIEW_PARITY: shared authenticated workspace presentation. */
const workspaceDescriptions = {
  customer: {
    overview: "Your next fitting, active orders and useful shortcuts in one calm workspace.",
    browse: "Compare approved tailoring professionals by service, location, availability and price.",
    profile: "Review the selected tailor's services, portfolio, availability, reviews and booking options.",
    account: "Keep your contact details and TailoraHub account information easy to review.",
    favorites: "Return to the ateliers you saved and book when the time feels right.",
    updates: "Follow booking, payment, OTP and order notifications in one timeline.",
    wallet: "Review available credit, reserved amounts and wallet activity.",
    referrals: "Invite people you trust and track eligible referral activity.",
    requests: "Review booking requests, confirmations and actions still needed.",
    orders: "Follow every garment from booking and measurement through handover.",
    support: "Raise a ticket and keep support connected to the relevant order.",
  },
  tailor: {
    overview: "Today's workboard brings requests, due orders, availability and earnings into focus.",
    profile: "Review the public atelier identity customers see before they book.",
    availability: "Control booking mode, slot capacity and working availability with confidence.",
    wallet: "Track earnings, settlements, withdrawals and reserved balances.",
    referrals: "Review your referral network, activations and eligible rewards.",
    media: "Present your craftsmanship through a polished photo and video portfolio.",
    services: "Maintain service prices, delivery times and customer-facing availability.",
    offers: "Create and manage offers without obscuring standard pricing.",
    followers: "Understand who follows your atelier and how interest is growing.",
    requests: "Review new booking requests before their response window closes.",
    waiting: "Move customers into newly available slots in a clear, fair order.",
    orders: "Organise measurement, stitching, quality check and handover work.",
    updates: "Stay on top of requests, payments, order changes and platform notices.",
    support: "Get help while keeping the relevant customer or order visible.",
  },
};

function RoleSidebarBrand({ role, screenCount }) {
  const roleLabel = role === "tailor" ? "Tailor" : "Customer";
  return (
    <div className="role-sidebar-brand">
      <span className="role-sidebar-monogram">TH</span>
      <span>
        <strong>TailoraHub</strong>
        <small>{roleLabel} workspace · {screenCount} screens</small>
      </span>
    </div>
  );
}

function WorkspacePageHeading({ role, panelId, label }) {
  const description = workspaceDescriptions[role]?.[panelId] || `Review and manage ${String(label || "this section").toLowerCase()} in TailoraHub.`;
  return (
    <header className={`workspace-page-heading workspace-page-heading-${panelId}`}>
      <span>{role} workspace</span>
      <h1>{label}</h1>
      <p>{description}</p>
    </header>
  );
}

function CustomerApp({ onLogout }) {
  const t = useT();
  const { language, setLanguage } = useLanguage();
  const [account, setAccount] = useState(null);
  const [tailors, setTailors] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [bookings, setBookings] = useState({ requests: [], orders: [], notifications: [] });
  const [filters, setFilters] = useState({ q: "", availability: "", ratingMin: "", service: "", distanceKm: "" });
  const [radiusKm, setRadiusKm] = useState(50);
  const [geo, setGeo] = useState({ latitude: null, longitude: null, status: "detecting", message: "Detecting your location..." });
  const [activePanel, setActivePanel] = useAppHistoryState("customerPanel", "overview");
  const [selectedTailorId, setSelectedTailorId] = useAppHistoryState("customerTailorId", "");
  const [selected, setSelected] = useState(null);
  const [profile, setProfile] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load(nextGeo = geo, nextRadius = radiusKm, silent = false) {
    if (!silent) setLoading(true);
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
      if (!silent) setLoading(false);
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
    setSelectedTailorId(tailor.id);
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

  useAutoRefresh(() => load(geo, radiusKm, true));

  useEffect(() => {
    if (activePanel !== "profile" || !selectedTailorId || profile?.tailor?.id === selectedTailorId) return undefined;
    let cancelled = false;
    setProfile(null);
    setError("");
    Promise.all([
      api.customerTailor(selectedTailorId),
      api.publicTailorServices(selectedTailorId).catch(() => null),
    ]).then(([detail, priceList]) => {
      if (cancelled) return;
      setProfile({ ...detail, services: priceList || detail.services || [] });
      setSelected(detail.tailor);
    }).catch((err) => {
      if (!cancelled) setError(err.message);
    });
    return () => { cancelled = true; };
  }, [activePanel, selectedTailorId, profile?.tailor?.id]);

  const unreadUpdates = unreadCount(bookings.notifications || []);
  const visibleTailors = useMemo(() => filterCustomerTailors(tailors, filters), [tailors, filters]);
  const customerDisplayName = account?.name || account?.fullName || "";
  const customerContact = account?.phone || account?.email || t("customer.findTrack", "Find and track tailoring");
  const customerHeaderTitle = customerDisplayName ? `Welcome, ${customerDisplayName}` : "Welcome";
  const customerInitials = String(customerDisplayName || "Customer").trim().split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "CU";

  async function openCustomerNotification(row) {
    await api.markCustomerNotificationRead(row.id);
    setBookings((old) => ({ ...old, notifications: (old.notifications || []).map((item) => item.id === row.id ? { ...item, read: true, read_at: new Date().toISOString() } : item) }));
    const entityId = row.entity_id || row.order_id || row.booking_request_id;
    const entityType = String(row.entity_type || "booking").toLowerCase();
    setActivePanel(entityType === "request" || entityType === "booking_request" ? "requests" : "orders");
    const url = new URL(window.location.href);
    if (entityId) url.searchParams.set(entityType.includes("request") ? "requestId" : "orderId", entityId);
    window.history.replaceState(currentHistoryState(), "", `${url.pathname}${url.search}${url.hash}`);
  }

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
    setSelectedTailorId("");
    setSelected(null);
    setProfile(null);
    setActivePanel("orders");
    await load();
  }

  const panels = [
    ["overview", t("common.overview", "Overview"), LayoutDashboard, null],
    ["browse", t("customer.panel.browse", "Browse Tailors"), Search, null],
    ["profile", t("customer.panel.profile", "Selected Tailor"), Scissors, null],
    ["favorites", t("common.favorites", "Favorites"), Heart, favorites.length],
    ["orders", t("common.orders", "My Orders"), Scissors, (bookings.orders || []).length],
    ["requests", t("common.requests", "Requests"), ClipboardList, (bookings.requests || []).length],
    ["updates", t("common.updates", "Updates"), Bell, unreadUpdates],
    ["wallet", t("common.wallet", "Wallet"), CreditCard, null],
    ["referrals", t("common.referrals", "Refer & Earn"), UsersRound, null],
    ["support", t("common.support", "Help & Support"), AlertTriangle, null],
    ["account", "Profile", UsersRound, null],
  ];
  const activePanelMeta = panels.find(([id]) => id === activePanel) || panels[0];
  const mobilePanels = ["overview", "orders", "requests", "updates", "wallet"]
    .map((id) => panels.find((panel) => panel[0] === id))
    .filter(Boolean)
    .map((panel) => panel[0] === "orders" ? [panel[0], "My", panel[2], panel[3]] : panel);
  const mobileTitle = panels.find((panel) => panel[0] === activePanel)?.[1] || "Customer workspace";
  const selectCustomerPanel = (id) => {
    setActivePanel(id);
    setMobileMenuOpen(false);
  };

  return (
    <Shell
      variant="customer"
      title={customerHeaderTitle}
      subtitle={t("dashboard.customer.subtitle", "Browse and book approved tailors")}
      icon={UsersRound}
      onLogout={onLogout}
      searchValue={filters.q}
      onSearch={(value) => {
        setFilters((old) => ({ ...old, q: value }));
        setActivePanel("browse");
      }}
      onUpdates={() => selectCustomerPanel("updates")}
      avatarLabel={customerInitials}
      unread={unreadUpdates}
      mobileTitle={mobileTitle}
      onMobileMenu={() => setMobileMenuOpen((open) => !open)}
      mobileMenuOpen={mobileMenuOpen}
    >
      <div className="customer-workspace">
        {mobileMenuOpen ? <button type="button" className="workspace-mobile-backdrop" onClick={() => setMobileMenuOpen(false)} aria-label="Close workspace navigation" /> : null}
        <aside className={`customer-side-card ${mobileMenuOpen ? "mobile-open" : ""}`}>
          <RoleSidebarBrand role="customer" screenCount={panels.length} />
          <nav className="tailor-side-nav">
            {panels.map(([id, label, Icon, count]) => (
              <button key={id} className={activePanel === id ? "active" : ""} onClick={() => selectCustomerPanel(id)}>
                <Icon size={16} />
                <span>{label}</span>
                {count ? <b>{count}</b> : null}
              </button>
            ))}
          </nav>
          <div className="customer-sidebar-footer">
            <div className="customer-sidebar-tools">
              <LanguageSelect language={language} setLanguage={setLanguage} />
              <button className="icon-btn" onClick={() => load()} title={t("common.refresh", "Refresh")}><RefreshCw size={17} /></button>
              <button className="icon-btn" onClick={onLogout} title={t("common.logout", "Logout")}><LogOut size={17} /></button>
            </div>
            <div className="customer-sidebar-user">
              <CustomerAvatar customer={account || { name: customerDisplayName }} size="md" />
              <span><strong>{customerDisplayName || "Customer"}</strong><small>{customerContact}</small></span>
            </div>
          </div>
        </aside>
        <WorkspaceMobileNav panels={mobilePanels} activePanel={activePanel} onSelect={selectCustomerPanel} />
        <div className="customer-content">
          {error ? <div className="error banner">{error}</div> : null}
          {loading ? <div className="loading">{t("customer.loading", "Loading customer data...")}</div> : null}
          <WorkspacePageHeading role="customer" panelId={activePanel} label={activePanelMeta[1]} />
          {activePanel === "overview" ? <CustomerOverviewPanel account={account} tailors={visibleTailors} favorites={favorites} bookings={bookings} onNavigate={setActivePanel} /> : null}
          {activePanel === "browse" ? <CustomerBrowsePanel filters={filters} setFilters={setFilters} allTailors={tailors} tailors={visibleTailors} openProfile={openProfile} onBook={openProfile} onFavorite={toggleFavorite} onFollow={toggleFollow} geo={geo} radiusKm={radiusKm} setRadiusKm={setRadiusKm} /> : null}
          {activePanel === "profile" ? (
            selected && profile ? <CustomerTailorProfile profile={profile} reload={load} onFavorite={toggleFavorite} onFollow={toggleFollow} onBookingCreated={handleBookingCreated} /> : <Empty text={t("customer.selectTailorEmpty", "Select a tailor from Browse Tailors to see profile, services, reviews, availability and booking form.")} />
          ) : null}
          {activePanel === "favorites" ? <CustomerFavoritesPanel tailors={favorites} openProfile={openProfile} onFavorite={toggleFavorite} onFollow={toggleFollow} /> : null}
          {activePanel === "updates" ? <Updates title={t("customer.updatesTitle", "Customer Updates")} rows={bookings.notifications || []} onOpen={openCustomerNotification} /> : null}
          {activePanel === "wallet" ? <CustomerWalletPanel /> : null}
          {activePanel === "referrals" ? <CustomerReferralPanel /> : null}
          {activePanel === "requests" ? <CustomerRequests rows={bookings.requests || []} /> : null}
          {activePanel === "orders" ? <CustomerOrders rows={bookings.orders || []} reload={load} onCreate={() => setActivePanel("browse")} /> : null}
          {activePanel === "support" ? <SupportPanel role="customer" orders={bookings.orders || []} /> : null}
          {activePanel === "account" ? <CustomerAccountPanel account={account} onNavigate={setActivePanel} /> : null}
        </div>
      </div>
    </Shell>
  );
}

function CustomerOverviewPanel({ account, tailors, favorites, bookings, onNavigate }) {
  const orders = bookings?.orders || [];
  const requests = bookings?.requests || [];
  const updates = bookings?.notifications || [];
  const closedStatuses = new Set(["COMPLETED", "CANCELLED", "REJECTED", "CLOSED"]);
  const activeOrders = orders.filter((row) => !closedStatuses.has(String(row.status || "").toUpperCase()));
  const pendingRequests = requests.filter((row) => !closedStatuses.has(String(row.status || "").toUpperCase()));
  const priorityOrder = activeOrders[0] || orders[0] || null;
  const orderName = priorityOrder?.serviceName || priorityOrder?.service_name || priorityOrder?.service || priorityOrder?.garment || "Tailoring order";
  const orderPartner = priorityOrder?.tailorShop || priorityOrder?.tailor_shop || priorityOrder?.shop || priorityOrder?.tailorName || priorityOrder?.tailor_name || "Assigned atelier";
  const orderDate = priorityOrder?.deliveryDate || priorityOrder?.delivery_date || priorityOrder?.appointmentDate || priorityOrder?.appointment_date;
  const parsedOrderDate = orderDate ? new Date(orderDate) : null;
  const hasValidOrderDate = parsedOrderDate && !Number.isNaN(parsedOrderDate.getTime());
  const orderMonth = hasValidOrderDate ? parsedOrderDate.toLocaleDateString("en-IN", { month: "short" }) : "NEXT";
  const orderDay = hasValidOrderDate ? parsedOrderDate.getDate() : "—";
  const orderYear = hasValidOrderDate ? parsedOrderDate.getFullYear() : "STEP";

  return (
    <div className="approved-overview-screen">
      <div className="kpi-grid approved-kpi-grid">
        <Kpi label="Active orders" value={activeOrders.length} icon={Scissors} />
        <Kpi label="Approved tailors" value={tailors.length} icon={UsersRound} />
        <Kpi label="Favorites" value={favorites.length} icon={Heart} />
        <Kpi label="Unread updates" value={unreadCount(updates)} icon={Bell} />
      </div>

      <div className="approved-overview-grid">
        <section className="section-block approved-priority-card">
          <div className="section-head">
            <div><span className="approved-card-eyebrow">Priority</span><h2>{priorityOrder ? "Your active order" : `Welcome${account?.name ? `, ${account.name}` : ""}`}</h2></div>
            <button type="button" className="text-link" onClick={() => onNavigate(priorityOrder ? "orders" : "browse")}>{priorityOrder ? "View order" : "Browse tailors"} <ArrowRight size={15} /></button>
          </div>
          {priorityOrder ? (
            <article className="approved-order-highlight">
              <span className="approved-date-tile"><small>{orderMonth}</small><strong>{orderDay}</strong><small>{orderYear}</small></span>
              <div><StatusPill value={priorityOrder.status} /><h3>{orderName}</h3><p>{orderPartner}</p><small>{orderDate ? `Expected ${fmtDay(orderDate)}` : "Open the order for its complete timeline."}</small></div>
              <button type="button" className="primary-btn" onClick={() => onNavigate("orders")}>Open details <ArrowRight size={15} /></button>
            </article>
          ) : (
            <div className="approved-empty-hero"><Scissors size={25} /><div><h3>Start with the right atelier</h3><p>Browse approved TailoraHub professionals and create your first booking request.</p></div><button type="button" className="primary-btn" onClick={() => onNavigate("browse")}>Find a tailor <ArrowRight size={15} /></button></div>
          )}
          <div className="approved-progress-track" aria-label="TailoraHub order journey">
            {["Booked", "Measured", "In progress", "Handover"].map((step, index) => <span className={priorityOrder && index < 2 ? "complete" : ""} key={step}><i>{index + 1}</i><small>{step}</small></span>)}
          </div>
        </section>

        <section className="approved-concierge-card">
          <span className="approved-concierge-icon"><Crown size={21} /></span>
          <small>TailoraHub concierge</small>
          <h2>Need a little help?</h2>
          <p>Support stays connected to the relevant booking, order or payment.</p>
          <button type="button" className="secondary-btn" onClick={() => onNavigate("support")}>Start a conversation <ArrowRight size={15} /></button>
        </section>
      </div>

      <section className="section-block approved-action-section">
        <div className="section-head"><div><span className="approved-card-eyebrow">Continue</span><h2>Quick actions</h2></div><small>{pendingRequests.length} request{pendingRequests.length === 1 ? "" : "s"} need attention</small></div>
        <div className="approved-quick-grid">
          {[["browse", "Browse tailors", UsersRound], ["orders", "Track orders", Scissors], ["requests", "Review requests", ClipboardList], ["wallet", "Open wallet", CreditCard]].map(([id, label, Icon]) => <button type="button" key={id} onClick={() => onNavigate(id)}><Icon size={19} /><strong>{label}</strong><ArrowRight size={15} /></button>)}
        </div>
      </section>
    </div>
  );
}

function LegacyCustomerOverviewPanel({ customerName, tailors, favorites, bookings, onBrowse, onOrders }) {
  const activeOrders = (bookings.orders || []).filter((row) => !["DELIVERED", "COMPLETED", "CANCELLED", "REJECTED"].includes(String(row.status || "").toUpperCase())).length;
  return (
    <section className="customer-overview-page">
      <header className="customer-page-heading">
        <div>
          <span className="customer-page-eyebrow">Customer workspace</span>
          <h1>{customerName ? `Welcome, ${customerName.split(/\s+/)[0]}` : "Welcome"}</h1>
          <p>Find verified tailors, manage bookings, and follow every order through delivery.</p>
        </div>
        <button type="button" className="primary-btn customer-heading-action" onClick={onBrowse}>Find a tailor <ArrowRight size={17} /></button>
      </header>
      <div className="customer-overview-stats">
        <button type="button" onClick={onBrowse}><Search size={19} /><span><small>Approved tailors</small><strong>{tailors.length}</strong></span></button>
        <button type="button" onClick={onOrders}><Scissors size={19} /><span><small>Active orders</small><strong>{activeOrders}</strong></span></button>
        <button type="button" onClick={onBrowse}><Heart size={19} /><span><small>Favorite tailors</small><strong>{favorites.length}</strong></span></button>
        <button type="button" onClick={onOrders}><ClipboardList size={19} /><span><small>Booking requests</small><strong>{(bookings.requests || []).length}</strong></span></button>
      </div>
    </section>
  );
}

function WorkspaceMobileNav({ panels, activePanel, onSelect }) {
  return (
    <nav className="workspace-mobile-nav" aria-label="Mobile workspace navigation">
      {panels.map(([id, label, Icon, count]) => (
        <button type="button" key={id} className={activePanel === id ? "active" : ""} onClick={() => onSelect(id)}>
          <span><Icon size={18} />{count ? <b>{count}</b> : null}</span>
          <small>{label}</small>
        </button>
      ))}
    </nav>
  );
}

function CustomerBrowsePanel({ filters, setFilters, allTailors, tailors, openProfile, onBook, onFavorite, onFollow, geo, radiusKm, setRadiusKm }) {
  const t = useT();
  const filterAreaRef = useRef(null);
  const searchInputRef = useRef(null);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [activeFilterGroup, setActiveFilterGroup] = useState("service");
  const [sortBy, setSortBy] = useState("nearest");
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
  const sortedTailors = useMemo(() => {
    const rows = [...tailors];
    if (sortBy === "rating") return rows.sort((a, b) => Number(b.rating || 0) - Number(a.rating || 0));
    if (sortBy === "price") return rows.sort((a, b) => Number(a.startingPrice || 0) - Number(b.startingPrice || 0));
    return rows.sort((a, b) => Number(a.distanceKm ?? Number.POSITIVE_INFINITY) - Number(b.distanceKm ?? Number.POSITIVE_INFINITY));
  }, [tailors, sortBy]);

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
    <section className="section-block no-top customer-browse-panel">
      <header className="customer-page-heading customer-browse-heading">
        <div>
          <span className="customer-page-eyebrow">Customer workspace</span>
          <h1>Browse tailors</h1>
          <p>Compare verified tailoring professionals by service, location, availability and price.</p>
        </div>
        <button type="button" className="primary-btn customer-heading-action" onClick={() => searchInputRef.current?.focus()}>Find a tailor <ArrowRight size={17} /></button>
      </header>
      <section className={filtersOpen ? "toolbar customer-live-toolbar filter-open" : "toolbar customer-live-toolbar"}>
        <div className="live-search-wrap" ref={filterAreaRef}>
          <div className="live-search-line">
            <label className="search live-search">
              <Search size={16} />
              <input
                ref={searchInputRef}
                value={filters.q}
                onChange={(e) => {
                  updateFilter({ q: e.target.value });
                  setSuggestionsOpen(true);
                }}
                onFocus={() => setSuggestionsOpen(true)}
                onBlur={() => window.setTimeout(() => setSuggestionsOpen(false), 120)}
                placeholder={t("customer.searchPlaceholder", "Search tailor, service or location")}
              />
            </label>
            <select className="customer-sort-select" value={sortBy} onChange={(event) => setSortBy(event.target.value)} aria-label="Sort tailors">
              <option value="nearest">Nearest first</option>
              <option value="rating">Highest rated</option>
              <option value="price">Lowest price</option>
            </select>
            <button
              type="button"
              className={filtersOpen ? "filter-menu-btn active" : "filter-menu-btn"}
              onClick={() => setFiltersOpen((open) => !open)}
              aria-label="Search filters"
              aria-expanded={filtersOpen}
              title="Filters"
            >
              <SlidersHorizontal size={17} />
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
      <small className="filter-result-count customer-result-count">{tailors.length} tailor{tailors.length === 1 ? "" : "s"} match your filters.</small>
      <PaginatedCards
        items={sortedTailors}
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

function TailorCard({ tailor, onOpen, onBook, onFavorite }) {
  const t = useT();
  const disabled = tailor.availability === "NOT_AVAILABLE" || !tailor.acceptingRequests;
  const firstMedia = portfolioItems(tailor.portfolio)[0];
  const shopInitials = String(tailor.shop || "TH").trim().split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "TH";
  const specialties = (tailor.expertise || []).slice(0, 3).join(" · ") || "Custom stitching";
  return (
    <article className="record-card tailor-card customer-discovery-card">
      <div className="tailor-card-cover">
        {firstMedia ? (
          firstMedia.kind === "video" ? <video src={firstMedia.url} muted preload="metadata" /> : <img src={firstMedia.url} alt={`${tailor.shop} cover`} loading="lazy" decoding="async" />
        ) : (
          <div className="tailor-cover-fallback">
            <span className="tailor-cover-monogram">{shopInitials}</span>
          </div>
        )}
        <button
          type="button"
          className={tailor.favoritedByMe ? "tailor-cover-favorite active" : "tailor-cover-favorite"}
          onClick={() => onFavorite(tailor)}
          aria-label={tailor.favoritedByMe ? t("customer.removeFavorite", "Remove favorite") : t("customer.addFavorite", "Add favorite")}
          aria-pressed={Boolean(tailor.favoritedByMe)}
        >
          <Heart size={19} fill={tailor.favoritedByMe ? "currentColor" : "none"} />
        </button>
      </div>
      <div className="tailor-card-body">
        <div className="tailor-card-trust-row">
          <span className="tailor-verified-label"><BadgeCheck size={14} /> {tailor.verified ? "Verified atelier" : "Approved tailor"}</span>
          <span className="tailor-card-rating"><Star size={14} fill="currentColor" /> {Number(tailor.rating || 0).toFixed(1)}</span>
        </div>
        <div className="tailor-card-title customer-tailor-title">
          <h3>{tailor.shop}</h3>
          <p title={specialties}>{specialties}</p>
        </div>
        <div className="tailor-card-facts">
          <span><MapPin size={14} /><b>{tailor.distanceKm !== undefined ? `${Number(tailor.distanceKm).toFixed(1)} km` : (tailor.zoneId || "Local")}</b></span>
          <span><CreditCard size={14} /><small>{t("customer.fromPrice", "From")}</small><b>{money(tailor.startingPrice)}</b></span>
          <StatusPill value={tailor.availability} />
        </div>
        <div className="inline-actions tailor-discovery-actions">
          <button className="secondary-btn" onClick={onOpen}>{t("customer.viewProfile", "View profile")}</button>
          <button className="primary-btn compact-action" onClick={onBook} disabled={disabled}>
            {disabled ? t("common.unavailable", "Unavailable") : t("customer.book", "Book now")}
            {!disabled ? <ArrowRight size={16} /> : null}
          </button>
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
                {mediaKind === "video" ? <video src={mediaUrl} controls preload="metadata" /> : <img src={mediaUrl} alt={offer.title} loading="lazy" decoding="async" />}
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
  const [serviceId, setServiceId] = useState("");
  const [form, setForm] = useState({ quantity: 1, requirements: "", preferredDate: "", urgentDays: "", instructions: "", measurementMode: "customer_visits_tailor", homeLocation: null, appointmentDate: "", appointmentSlot: "" });
  const [previewData, setPreviewData] = useState(null);
  const [confirmation, setConfirmation] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [bookingStep, setBookingStep] = useState(() => new URLSearchParams(window.location.search).get("bookingStep") || "details");
  const [showHomeMap, setShowHomeMap] = useState(false);
  const [message, setMessage] = useState("");
  const [clockMinute, setClockMinute] = useState(() => Math.floor(Date.now() / 60000));
  const disabled = tailor.availability === "NOT_AVAILABLE" || !tailor.acceptingRequests;
  const selectedService = useMemo(() => serviceRows.find((s) => s.id === serviceId) || null, [serviceRows, serviceId]);
  const bookingQuantity = Math.max(1, Number(form.quantity || 1));
  const garmentsPerService = selectedService?.isCombo ? Math.max(2, selectedService.comboItems.length || 0) : 1;
  const totalGarmentQuantity = bookingQuantity * garmentsPerService;
  const urgentOptions = [
    { days: 1, charge: 150 },
    { days: 2, charge: 100 },
    { days: 3, charge: 50 },
  ];
  const urgentCharge = urgentOptions.find((option) => String(option.days) === String(form.urgentDays))?.charge || 0;
  const urgentDeliveryDate = form.urgentDays ? addDaysToDateInput(todayDateInput(), Math.max(0, Number(form.urgentDays) - 1)) : "";
  const serviceAmount = Number(selectedService?.price || 0) * bookingQuantity;
  const bookingEstimateTotal = serviceAmount + urgentCharge;
  const measurementCutoff = useMemo(() => {
    if (!form.preferredDate) return null;
    const deadline = new Date(`${form.preferredDate}T00:00:00`);
    deadline.setDate(deadline.getDate() + 1);
    deadline.setHours(deadline.getHours() - (form.urgentDays ? 12 : 48));
    return deadline;
  }, [form.preferredDate, form.urgentDays]);
  const latestAppointmentDate = useMemo(() => {
    if (!measurementCutoff) return "";
    const latest = new Date(measurementCutoff);
    if (!form.urgentDays) latest.setDate(latest.getDate() - 1);
    return [latest.getFullYear(), String(latest.getMonth() + 1).padStart(2, "0"), String(latest.getDate()).padStart(2, "0")].join("-");
  }, [measurementCutoff, form.urgentDays]);
  const availableAppointmentSlots = useMemo(() => {
    if (!form.appointmentDate) return [];
    const appointmentDate = form.appointmentDate;
    const now = new Date(clockMinute * 60000);
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    return APPOINTMENT_TIME_SLOTS.filter((slot) => {
      if (appointmentDate === todayDateInput() && slot.startMinutes <= currentMinutes) return false;
      if (!measurementCutoff) return false;
      const end = new Date(`${appointmentDate}T00:00:00`);
      end.setMinutes(slot.startMinutes + 120);
      return end <= measurementCutoff;
    });
  }, [form.appointmentDate, clockMinute, measurementCutoff]);

  useEffect(() => {
    const timer = window.setInterval(() => setClockMinute(Math.floor(Date.now() / 60000)), 30000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (form.appointmentSlot && !availableAppointmentSlots.some((slot) => slot.value === form.appointmentSlot)) {
      setForm((old) => ({ ...old, appointmentSlot: "" }));
    }
  }, [availableAppointmentSlots, form.appointmentSlot]);

  const draftKey = `tailorahub:booking-draft:${tailor.id}`;
  const confirmationKey = `tailorahub:booking-confirmation:${tailor.id}`;
  function changeBookingStep(step) {
    const url = new URL(window.location.href);
    if (step === "details") url.searchParams.delete("bookingStep");
    else url.searchParams.set("bookingStep", step);
    window.history.pushState(currentHistoryState(), "", `${url.pathname}${url.search}${url.hash}`);
    setBookingStep(step);
  }

  useEffect(() => {
    const restoreStep = () => setBookingStep(new URLSearchParams(window.location.search).get("bookingStep") || "details");
    window.addEventListener("popstate", restoreStep);
    return () => window.removeEventListener("popstate", restoreStep);
  }, []);

  useEffect(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(draftKey) || "null");
      if (saved?.tailorId === tailor.id) {
        setServiceId(saved.serviceId || "");
        setForm((old) => ({ ...old, ...(saved.form || {}) }));
      } else {
        setServiceId("");
      }
      setConfirmation(JSON.parse(sessionStorage.getItem(confirmationKey) || "null"));
    } catch {
      sessionStorage.removeItem(draftKey);
      sessionStorage.removeItem(confirmationKey);
    }
  }, [tailor.id]);

  function update(key, value) {
    setForm((old) => {
      const next = { ...old, [key]: value };
      if (["preferredDate", "urgentDays"].includes(key)) next.appointmentSlot = "";
      if (key === "preferredDate" && next.appointmentDate && next.appointmentDate > value) {
        next.appointmentDate = "";
      }
      if (key === "measurementMode" && value !== "tailor_visits_customer") {
        next.homeLocation = null;
      }
      return next;
    });
  }

  function updateCompletionSpeed(value) {
    const preferredDate = value ? addDaysToDateInput(todayDateInput(), Math.max(0, Number(value) - 1)) : "";
    setForm((old) => ({
      ...old,
      urgentDays: value,
      preferredDate,
      appointmentDate: old.appointmentDate && preferredDate && old.appointmentDate <= preferredDate ? old.appointmentDate : "",
      appointmentSlot: "",
    }));
  }

  function bookingPayload(idempotencyKey) {
    const service = selectedService || serviceRows.find((s) => s.id === serviceId);
    return {
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
      urgentDays: form.urgentDays ? Number(form.urgentDays) : null,
      customerLocationAddress: form.measurementMode === "tailor_visits_customer" ? form.homeLocation?.address_text : undefined,
      customerLocationLat: form.measurementMode === "tailor_visits_customer" ? form.homeLocation?.latitude : undefined,
      customerLocationLng: form.measurementMode === "tailor_visits_customer" ? form.homeLocation?.longitude : undefined,
      ...(idempotencyKey ? { idempotencyKey } : {}),
    };
  }

  async function previewBooking(event) {
    event.preventDefault();
    setMessage("");
    const service = selectedService || serviceRows.find((s) => s.id === serviceId);
    const today = todayDateInput();
    if (!service || !serviceId) {
      setMessage("Select a service before sending the booking request.");
      return;
    }
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
    if (!form.appointmentSlot || !availableAppointmentSlots.some((slot) => slot.value === form.appointmentSlot)) {
      setMessage("Choose an available future appointment time slot.");
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
      const existing = JSON.parse(sessionStorage.getItem(draftKey) || "null");
      const idempotencyKey = existing?.idempotencyKey || crypto.randomUUID();
      const draft = { tailorId: tailor.id, serviceId, form, idempotencyKey };
      const result = await api.previewBooking(bookingPayload());
      sessionStorage.setItem(draftKey, JSON.stringify(draft));
      setPreviewData(result);
      changeBookingStep("preview");
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function submitBooking() {
    if (submitting) return;
    setSubmitting(true);
    setMessage("");
    try {
      const draft = JSON.parse(sessionStorage.getItem(draftKey) || "null");
      if (!draft?.idempotencyKey) throw new Error("Booking draft expired. Return to Edit and preview again.");
      await api.previewBooking(bookingPayload());
      const res = await api.createBooking(bookingPayload(draft.idempotencyKey));
      const savedConfirmation = { ...res, tailorShop: tailor.shop };
      sessionStorage.setItem(confirmationKey, JSON.stringify(savedConfirmation));
      sessionStorage.removeItem(draftKey);
      setConfirmation(savedConfirmation);
      changeBookingStep("confirmation");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (bookingStep !== "preview" || previewData) return;
    let cancelled = false;
    api.previewBooking(bookingPayload()).then((result) => {
      if (!cancelled) {
        setMessage("");
        setPreviewData(result);
      }
    }).catch((err) => {
      if (!cancelled) setMessage(err.message);
    });
    return () => { cancelled = true; };
  }, [bookingStep, serviceId]);

  async function finishConfirmation() {
    sessionStorage.removeItem(confirmationKey);
    setConfirmation(null);
    setPreviewData(null);
    setForm({ quantity: 1, requirements: "", preferredDate: "", urgentDays: "", instructions: "", measurementMode: "customer_visits_tailor", homeLocation: null, appointmentDate: "", appointmentSlot: "" });
    setShowHomeMap(false);
    changeBookingStep("details");
    if (onBookingCreated) await onBookingCreated(confirmation?.booking || confirmation);
    else await reload();
  }

  if (bookingStep === "confirmation" && confirmation) {
    return <BookingConfirmation confirmation={confirmation} onDone={finishConfirmation} />;
  }
  if (bookingStep === "preview") {
    return <BookingPreview preview={previewData} message={message} submitting={submitting} onEdit={() => changeBookingStep("details")} onSubmit={submitBooking} />;
  }

  return (
    <div className="profile-panel customer-tailor-profile">
      <section className="selected-tailor-summary">
        <div className="profile-heading">
          <TailorAvatar tailor={tailor} size="lg" />
          <div>
            <span className="selected-tailor-eyebrow">Selected atelier</span>
            <h3>{tailor.shop}</h3>
            <p>{tailor.ownerName} · {tailor.years} years experience</p>
          </div>
        </div>
        <div className="relationship-row profile-actions">
          <button className={tailor.favoritedByMe ? "mini-action active" : "mini-action"} type="button" aria-pressed={Boolean(tailor.favoritedByMe)} onClick={() => onFavorite(tailor)} title={tailor.favoritedByMe ? "Remove favorite" : "Add favorite"}>
            <Heart size={15} />
            <span>{tailor.favoritedByMe ? "Favorited" : "Favorite"}</span>
            <b>{tailor.favoriteCount || 0}</b>
          </button>
          <button className={tailor.followedByMe ? "mini-action active following-state" : "mini-action"} type="button" aria-pressed={Boolean(tailor.followedByMe)} onClick={() => onFollow(tailor)} title={tailor.followedByMe ? "Unfollow tailor" : "Follow tailor"}>
            {tailor.followedByMe ? <CheckCircle2 size={15} /> : <Bell size={15} />}
            <span>{tailor.followedByMe ? "Following" : "Follow"}</span>
            <b>{tailor.followerCount || 0}</b>
          </button>
        </div>
        <div className="selected-tailor-details">
          <div className="selected-tailor-detail-block selected-tailor-availability-block">
            <span className="selected-tailor-detail-label">Availability</span>
            <div className="selected-tailor-availability">
              <StatusPill value={tailor.availability} />
              <span>{tailor.availabilityNote || availabilityCopy[tailor.availability]}</span>
            </div>
          </div>
          <div className="selected-tailor-detail-block selected-tailor-about-block">
            <span className="selected-tailor-detail-label">About atelier</span>
            <p className="selected-tailor-bio">{tailor.bio || "No profile description yet."}</p>
          </div>
        </div>
      </section>
      <div className="selected-tailor-showcase">
        <section className="selected-tailor-mini-card">
          <div className="selected-tailor-section-head"><h3>Offers</h3><small>Current promotions</small></div>
          <OfferList offers={offers} />
        </section>
        <section className="selected-tailor-mini-card">
          <div className="selected-tailor-section-head"><h3>Photos and Videos</h3><small>Recent work</small></div>
          <MediaGallery portfolio={tailor.portfolio} />
        </section>
      </div>
      <section className="booking-request-section">
        <div className="booking-request-heading">
          <div>
            <span>Booking details</span>
            <h3>Send Booking Request</h3>
          </div>
          <small>Complete the details below, then review everything before submitting.</small>
        </div>
      {disabled ? <div className="notice">Currently Not Accepting New Orders</div> : (
        <form className="stack-form booking-request-form" onSubmit={previewBooking}>
          <label className="span-2">
            Service
            <select value={serviceId} onChange={(e) => setServiceId(e.target.value)} required>
              <option value="">Select a service</option>
              {serviceRows.map((service) => (
                <option key={service.id} value={service.id}>{service.name} - {money(service.price)}</option>
              ))}
            </select>
            {selectedService ? (
              <small>{selectedService.category}{selectedService.isCombo && selectedService.comboItems.length ? ` - Includes ${selectedService.comboItems.join(", ")}` : ""}{selectedService.description ? ` - ${selectedService.description}` : ""}</small>
            ) : <small>Choose a service to see its price.</small>}
          </label>
          <label>Quantity<input type="number" min="1" value={form.quantity} onChange={(e) => update("quantity", e.target.value)} /></label>
          <label>
            Completion speed
            <select value={form.urgentDays} onChange={(e) => updateCompletionSpeed(e.target.value)}>
              <option value="">Regular delivery</option>
              {urgentOptions.map((option) => <option key={option.days} value={option.days}>Within {option.days} day{option.days > 1 ? "s" : ""} (+{money(option.charge)})</option>)}
            </select>
            <small>Select regular delivery or one of the three faster completion options.</small>
          </label>
          <label className="booking-requirements span-2">Stitching requirements<textarea value={form.requirements} onChange={(e) => update("requirements", e.target.value)} /></label>
          <label>Expected delivery date<input type="date" value={form.preferredDate} min={urgentDeliveryDate || todayDateInput()} max={urgentDeliveryDate || undefined} onChange={(e) => update("preferredDate", e.target.value)} required /></label>
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
                  <LazyMapPicker
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
          ) : (
            <div className="booking-visit-summary span-2" role="note">
              <span>Measurement location</span>
              <strong>Visit the tailor's shop</strong>
              <small>{tailor.shopAddress || tailor.zoneId}</small>
            </div>
          )}
          {selectedService ? (
            <BookingEstimateCard
              serviceName={selectedService.name}
              serviceAmount={serviceAmount}
              quantity={bookingQuantity}
              totalGarments={totalGarmentQuantity}
              urgentDays={form.urgentDays ? Number(form.urgentDays) : null}
              urgentCharge={urgentCharge}
              total={bookingEstimateTotal}
            />
          ) : null}
          <label>
            Measurement appointment date
            <input
              type="date"
              value={form.appointmentDate}
              min={todayDateInput()}
              max={latestAppointmentDate || undefined}
              disabled={!form.preferredDate}
              onChange={(e) => update("appointmentDate", e.target.value)}
              required
            />
            <small>{measurementCutoff ? `Measurement must finish by ${measurementCutoff.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}. Later dates and slots are disabled.` : "Choose expected delivery date first."}</small>
          </label>
          <label>
            Appointment time
            <select value={form.appointmentSlot} onChange={(e) => update("appointmentSlot", e.target.value)} disabled={!form.appointmentDate || availableAppointmentSlots.length === 0} required>
              <option value="">{!form.appointmentDate ? "Choose appointment date first" : availableAppointmentSlots.length ? "Select a time slot" : "No available slots before the measurement cutoff"}</option>
              {availableAppointmentSlots.map((slot) => <option key={slot.value} value={slot.value}>{slot.label}</option>)}
            </select>
          </label>
          <label className="booking-special-instructions span-2">Special instructions<textarea value={form.instructions} onChange={(e) => update("instructions", e.target.value)} /></label>
          <div className="booking-form-actions span-2">
            <div>
              <strong>Ready to review?</strong>
              <small>Your booking will not be created until you confirm it on the preview page.</small>
            </div>
            <button className="primary-btn">Preview Booking</button>
          </div>
        </form>
      )}
      {message ? <div className={message.includes("waiting list") ? "notice waiting-notice" : message.includes("Booking") || message.includes("approved") ? "notice ok" : "error"}>{message.includes("waiting list") ? <><span className="live-dot" /> {message}</> : message}</div> : null}
      </section>
      <section className="selected-tailor-reviews">
        <div className="selected-tailor-section-head"><h3>Reviews</h3><small>Verified customer feedback</small></div>
        <ViewMoreGrid
          items={reviews}
          initial={4}
          step={4}
          className="review-list"
          label="reviews"
          emptyText="No public reviews yet."
          renderItem={(review) => <ReviewCard review={review} />}
        />
      </section>
    </div>
  );
}

function BookingEstimateCard({
  serviceName,
  serviceAmount,
  quantity,
  totalGarments,
  urgentDays,
  urgentCharge,
  total,
}) {
  return (
    <div className="booking-estimate-card span-2">
      <div className="booking-estimate-head">
        <div>
          <span>Price estimate</span>
          <strong>{serviceName}</strong>
        </div>
        <b>{money(total)}</b>
      </div>
      <div className="booking-estimate-row">
        <span>Service amount x {quantity} ({totalGarments} garment{totalGarments === 1 ? "" : "s"})</span>
        <strong>{money(serviceAmount)}</strong>
      </div>
      {urgentDays ? <div className="booking-estimate-row"><span>Within {urgentDays} day{urgentDays > 1 ? "s" : ""} urgent charge</span><strong>{money(urgentCharge)}</strong></div> : null}
      <div className="booking-estimate-row total">
        <span>Service total</span>
        <strong>{money(total)}</strong>
      </div>
      <small>Any applicable final charges are shown for confirmation before payment.</small>
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

function CustomerOrders({ rows, reload, onCreate }) {
  const [filter, setFilter] = useState("all");
  const activeOrders = rows.filter((order) => !isClosedOrder(order) && !isCancelledCustomerOrder(order));
  const completedOrders = rows.filter((order) => isClosedOrder(order) && !isCancelledCustomerOrder(order));
  const today = todayDateInput();
  const upcomingOrders = activeOrders.filter((order) => {
    const nextDate = orderDateInput(order.appointmentDate || order.appointment_date || order.expectedCompletion || order.expected_completion);
    return !nextDate || nextDate >= today;
  });
  const filters = [
    ["all", "All", rows],
    ["active", "Active", activeOrders],
    ["upcoming", "Upcoming", upcomingOrders],
    ["completed", "Completed", completedOrders],
  ];
  const activeFilter = filters.find(([key]) => key === filter) || filters[0];
  const activeRows = activeFilter[2];

  return (
    <section className="section-block no-top customer-orders-page">
      <div className="customer-orders-hero">
        <div>
          <span className="customer-orders-eyebrow">Customer workspace</span>
          <h3>My orders</h3>
          <p>Follow every garment from booking and measurement through delivery.</p>
        </div>
        <button type="button" className="primary-btn customer-create-booking" onClick={onCreate}>Create booking <ArrowRight size={18} /></button>
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
          <PaginatedCards
            items={activeRows}
            pageSize={4}
            className="customer-order-card-list customer-order-timeline-list"
            label="orders"
            emptyText={`No ${activeFilter[1].toLowerCase()} orders right now.`}
            renderItem={(order) => <CustomerOrderCard order={order} reload={reload} />}
          />
        </>
      ) : <Empty text="No orders yet. Choose an approved tailor to create your first booking." />}
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

function trackerSocketUrl(orderId, ticket) {
  const query = new URLSearchParams({ ticket });
  return `${api.base.replace(/^http/, "ws")}/v1/bookings/${encodeURIComponent(orderId)}/track?${query}`;
}

function useBookingLiveUpdates(orderId, onPayload, fallbackRefresh, enabled = true) {
  const payloadRef = useRef(onPayload);
  const fallbackRef = useRef(fallbackRefresh);
  useEffect(() => { payloadRef.current = onPayload; }, [onPayload]);
  useEffect(() => { fallbackRef.current = fallbackRefresh; }, [fallbackRefresh]);

  useEffect(() => {
    if (!enabled || !orderId) return undefined;
    let closed = false;
    let socket;
    let reconnectTimer;
    let fallbackTimer;
    let heartbeatTimer;
    let connecting = false;

    function clearConnectionTimers() {
      window.clearInterval(heartbeatTimer);
      window.clearTimeout(reconnectTimer);
    }

    function startFallback() {
      if (closed || fallbackTimer) return;
      fallbackRef.current?.();
      fallbackTimer = window.setInterval(() => {
        if (document.visibilityState === "visible") fallbackRef.current?.();
      }, 60000);
    }

    function stopFallback() {
      window.clearInterval(fallbackTimer);
      fallbackTimer = undefined;
    }

    async function connect() {
      if (closed || connecting || document.visibilityState === "hidden" || socket?.readyState === WebSocket.OPEN || socket?.readyState === WebSocket.CONNECTING) return;
      connecting = true;
      clearConnectionTimers();
      try {
        const ticketResponse = await api.bookingTrackTicket(orderId);
        if (closed || document.visibilityState === "hidden") return;
        socket = new WebSocket(trackerSocketUrl(orderId, ticketResponse.ticket));
        socket.onopen = () => {
          stopFallback();
          heartbeatTimer = window.setInterval(() => {
            if (socket?.readyState === WebSocket.OPEN) socket.send("ping");
          }, 25000);
        };
        socket.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload?.type !== "pong") payloadRef.current?.(payload);
          } catch {}
        };
        socket.onerror = () => socket?.close();
        socket.onclose = () => {
          socket = undefined;
          window.clearInterval(heartbeatTimer);
          startFallback();
          if (!closed) reconnectTimer = window.setTimeout(connect, 10000);
        };
      } catch {
        startFallback();
        reconnectTimer = window.setTimeout(connect, 10000);
      } finally {
        connecting = false;
      }
    }

    function handleVisibility() {
      if (document.visibilityState === "visible") {
        fallbackRef.current?.();
        connect();
      } else if (socket) {
        socket.close();
      }
    }

    connect();
    window.addEventListener("online", connect);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      closed = true;
      clearConnectionTimers();
      stopFallback();
      window.removeEventListener("online", connect);
      document.removeEventListener("visibilitychange", handleVisibility);
      if (socket) socket.close();
    };
  }, [orderId, enabled]);
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
const razorpayKeyId = import.meta.env.VITE_RAZORPAY_KEY_ID || "";

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
      key: options.keyId || options.key_id || razorpayKeyId,
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

  useEffect(() => {
    if (sessionMessage) setInfo(sessionMessage);
  }, [sessionMessage]);
}

function CustomerAccountProfile({ account, onSupport }) {
  const displayName = account?.name || account?.fullName || "Customer";
  return (
    <section className="customer-account-profile section-block no-top">
      <div className="section-head customer-profile-heading">
        <div>
          <h3>Profile</h3>
          <p>Your account and verified contact information.</p>
        </div>
      </div>
      <div className="customer-profile-layout">
        <aside className="customer-profile-identity">
          <CustomerAvatar customer={account || { name: displayName }} size="xl" />
          <div>
            <h3>{displayName}</h3>
            <p>TailoraHub customer{account?.joined ? ` since ${fmtDay(account.joined)}` : ""}</p>
          </div>
          <StatusPill value={account?.status || "ACTIVE"} />
        </aside>
        <div className="customer-profile-details">
          <div className="customer-profile-details-head">
            <div>
              <small>Account details</small>
              <h3>Personal information</h3>
            </div>
            <button type="button" className="secondary-btn" onClick={onSupport}>Request changes</button>
          </div>
          <dl className="customer-profile-fields">
            <div><dt>Full name</dt><dd>{displayName}</dd></div>
            <div><dt>Mobile number</dt><dd>{account?.phone || "Not provided"}</dd></div>
            <div><dt>Email address</dt><dd>{account?.email || "Not provided"}</dd></div>
            <div><dt>Location / zone</dt><dd>{account?.zoneId || "Not provided"}</dd></div>
            <div className="wide"><dt>Primary address</dt><dd>{account?.address || "No address saved"}</dd></div>
          </dl>
          <p className="customer-profile-note">For security, use Help &amp; Support to change verified phone or email details.</p>
        </div>
      </div>
    </section>
  );
}

function CustomerAccountPanel({ account, onNavigate }) {
  const displayName = account?.name || account?.fullName || "TailoraHub customer";
  const contact = account?.phone || account?.email || "Contact information is not available.";
  return (
    <section className="section-block no-top approved-profile-layout">
      <aside className="approved-profile-summary">
        <CustomerAvatar customer={account || { name: displayName }} size="lg" />
        <BadgeCheck size={18} />
        <h2>{displayName}</h2>
        <p>TailoraHub customer account</p>
        <button type="button" className="secondary-btn" onClick={() => onNavigate("support")}>Get profile help</button>
      </aside>
      <div className="approved-profile-details">
        <div className="section-head"><div><span className="approved-card-eyebrow">Account details</span><h2>Personal information</h2></div></div>
        <dl>
          <div><dt>Full name</dt><dd>{displayName}</dd></div>
          <div><dt>Primary contact</dt><dd>{contact}</dd></div>
          <div><dt>Account role</dt><dd>Customer</dd></div>
          <div><dt>Profile ID</dt><dd>{account?.customerProfileId || account?.customer_profile_id || account?.id || "Available after profile sync"}</dd></div>
        </dl>
        <div className="approved-profile-actions">
          <button type="button" className="secondary-btn" onClick={() => onNavigate("referrals")}>Referral profile</button>
          <button type="button" className="primary-btn" onClick={() => onNavigate("browse")}>Browse tailors <ArrowRight size={15} /></button>
        </div>
      </div>
    </section>
  );
}

function TailorProfilePanel({ tailor, onNavigate }) {
  return (
    <section className="section-block no-top approved-profile-layout">
      <aside className="approved-profile-summary">
        <TailorAvatar tailor={tailor} size="lg" />
        <BadgeCheck size={18} />
        <h2>{tailor.shop || "Your atelier"}</h2>
        <p>{tailor.approvalStatus === "APPROVED" ? "Approved TailoraHub professional" : `Approval status: ${tailor.approvalStatus || "Pending"}`}</p>
        <StatusPill value={tailor.availability} />
      </aside>
      <div className="approved-profile-details">
        <div className="section-head"><div><span className="approved-card-eyebrow">Public presentation</span><h2>Atelier profile</h2></div></div>
        <dl>
          <div><dt>Owner</dt><dd>{tailor.ownerName || "—"}</dd></div>
          <div><dt>Atelier</dt><dd>{tailor.shop || "—"}</dd></div>
          <div><dt>Experience</dt><dd>{tailor.experienceDisplay || `${tailor.years || 0} years`}</dd></div>
          <div><dt>Location</dt><dd>{tailor.shopAddress || tailor.zoneId || "—"}</dd></div>
          <div className="span-two"><dt>About the atelier</dt><dd>{tailor.bio || "Add portfolio media and service information to strengthen your public profile."}</dd></div>
        </dl>
        <div className="approved-profile-actions">
          <button type="button" className="secondary-btn" onClick={() => onNavigate("media")}>Manage photos / videos</button>
          <button type="button" className="primary-btn" onClick={() => onNavigate("services")}>Manage services <ArrowRight size={15} /></button>
        </div>
      </div>
    </section>
  );
}

function BookingPreview({ preview, message, submitting, onEdit, onSubmit }) {
  if (!preview) {
    return <section className="section-block booking-preview"><h2>Booking Preview</h2>{message ? <div className="error">{message}</div> : <div className="loading">Validating booking details...</div>}<button type="button" className="secondary-btn" onClick={onEdit}>Edit</button></section>;
  }
  const slotLabel = APPOINTMENT_TIME_SLOTS.find((slot) => slot.value === preview.appointmentSlot)?.label || preview.appointmentSlot;
  const modeLabel = preview.measurementMode === "tailor_visits_customer" ? "Tailor visits customer" : "Customer visits tailor";
  return (
    <section className="section-block booking-preview">
      <div className="section-head"><div><small>Review all information before final submission</small><h2>Booking Preview</h2></div><StatusPill value={preview.expectedStatus} /></div>
      <div className="record-card"><h3>Tailor</h3><strong>{preview.tailor?.shop || "-"}</strong><p>{preview.tailor?.ownerName || ""}</p><small>{preview.tailor?.address || ""}</small></div>
      <div className="two-col">
        <div className="record-card"><h3>Service details</h3><p><strong>{preview.service?.name}</strong></p><p>Quantity: {preview.quantity}</p><p>Total garments: {preview.price?.totalGarments}</p><p>Expected delivery: {fmtDay(preview.expectedDeliveryDate)}</p>{preview.urgentDays ? <p>Completion speed: Within {preview.urgentDays} day{preview.urgentDays > 1 ? "s" : ""}</p> : <p>Completion speed: Regular</p>}</div>
        <div className="record-card"><h3>Measurement appointment</h3><p>{fmtDay(preview.appointmentDate)}</p><p>{slotLabel}</p><p>{modeLabel}</p><small>{preview.address || ""}</small></div>
        <div className="record-card"><h3>Customer details</h3><p>{preview.customer?.name || "-"}</p><p>{preview.customer?.phone || ""}</p><p>{preview.customer?.email || ""}</p></div>
        <div className="record-card"><h3>Requirements and instructions</h3><p>{preview.requirements || "No stitching requirements provided."}</p><p>{preview.instructions || "No special instructions provided."}</p></div>
      </div>
      <div className="record-card booking-preview-total"><h3>Price confirmation</h3><p>Service amount <strong>{money(preview.price?.baseAmount)}</strong></p><p>Urgent charge <strong>{money(preview.price?.urgentCharge)}</strong></p><h2>Total <strong>{money(preview.price?.finalAmount)}</strong></h2><small>Price and slot were validated by TailoraHub at {fmtDate(preview.validatedAt)} and will be checked again on submission.</small></div>
      {!preview.slotAvailable && preview.expectedStatus === "WAITLISTED" ? <div className="notice waiting-notice">The selected slot is full. Submitting will place this booking on the waiting list.</div> : null}
      {message ? <div className="error">{message}</div> : null}
      <div className="inline-actions"><button type="button" className="secondary-btn" onClick={onEdit} disabled={submitting}>Edit</button><button type="button" className="primary-btn" onClick={onSubmit} disabled={submitting}>{submitting ? "Submitting..." : "Submit Booking"}</button></div>
    </section>
  );
}

function BookingConfirmation({ confirmation, onDone }) {
  const booking = confirmation.booking || {};
  return (
    <section className="section-block booking-confirmation">
      <CheckCircle2 size={52} />
      <small>Booking submitted successfully</small>
      <h2>{confirmation.code || booking.code}</h2>
      <p>Your booking with {confirmation.tailorShop || "the selected tailor"} has been created.</p>
      <StatusPill value={confirmation.status || booking.status} />
      {confirmation.duplicate ? <div className="notice">This booking was already submitted earlier; no duplicate was created.</div> : null}
      <button type="button" className="primary-btn" onClick={onDone}>Return to Tailor Profile</button>
    </section>
  );
}

function PasswordInput({ ariaLabel = "Password", ...props }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="password-input-wrap">
      <input {...props} type={visible ? "text" : "password"} />
      <button
        type="button"
        className="password-visibility-btn"
        onClick={() => setVisible((current) => !current)}
        aria-label={`${visible ? "Hide" : "Show"} ${ariaLabel.toLowerCase()}`}
        title={`${visible ? "Hide" : "Show"} ${ariaLabel.toLowerCase()}`}
      >
        {visible ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div>
  );
}

function normalizeMeasurementModeValue(value) {
  return String(value || "").trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function isTailorVisitOrder(order) {
  return normalizeMeasurementModeValue(order?.measurementMode || order?.measurement_mode) === "tailor_visits_customer";
}

function isMeasurementArrivalVerified(order) {
  const status = String(order?.measurementTripStatus || order?.measurement_trip_status || "").toLowerCase();
  return Boolean(order?.measurementOtpVerifiedAt || order?.measurement_otp_verified_at || status === "otp_verified");
}

function tripStatusLabel(status) {
  const value = String(status || "not_started").toLowerCase();
  if (value === "en_route") return "Tailor is on the way";
  if (value === "arrived") return "Tailor reached customer location";
  if (value === "otp_verified") return "Arrival OTP verified";
  return "Tailor not started yet";
}

function mapLinkFor(lat, lng, address) {
  if (lat !== undefined && lat !== null && lng !== undefined && lng !== null) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${lat},${lng}`)}`;
  }

  if (address) return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
  return "https://www.google.com/maps";
}

function getBrowserCoordinates({ required = false } = {}) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      if (required) {
        reject(new Error("Location permission is required to share your live location."));
        return;
      }
      resolve({});
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      () => {
        if (required) {
          reject(new Error("Allow location permission in the browser before sharing live location."));
          return;
        }
        resolve({});
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 15000 }
    );
  });
}

async function uploadToPresignedPost(plan, file) {
  const form = new FormData();
  Object.entries(plan.fields || {}).forEach(([key, value]) => form.append(key, value));
  form.append("file", file);
  const response = await fetch(plan.uploadUrl, { method: "POST", body: form });
  if (!response.ok) throw new Error("The direct media upload failed. Please try again.");
}

function notifyBookingPanels(bookingId) {
  if (!bookingId || typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("tailorahub:booking-trip-refresh", { detail: { bookingId } }));
  window.dispatchEvent(new CustomEvent("tailorahub:orders-refresh", { detail: { bookingId } }));
}

function CustomerMeasurementVisitPanel({ order }) {
  const [trip, setTrip] = useState(order);
  const [error, setError] = useState("");

  async function loadTrip() {
    if (!order?.id) return;
    try {
      const res = await api.measurementTrip(order.id);
      setTrip(res.booking || order);
      setError("");
    } catch (err) {
      setError(err.message || "Visit tracking could not be loaded.");
    }
  }

  useEffect(() => {
    setTrip(order);
    loadTrip();
  }, [order?.id]);

  useEffect(() => {
    setTrip(order);
  }, [order]);

  useEffect(() => {
    function refreshTrip(event) {
      if (!event.detail?.bookingId || event.detail.bookingId === order?.id) loadTrip();
    }
    window.addEventListener("tailorahub:booking-trip-refresh", refreshTrip);
    return () => window.removeEventListener("tailorahub:booking-trip-refresh", refreshTrip);
  }, [order?.id]);

  if (!order?.id) return null;
  if (!isTailorVisitOrder(trip)) return null;

  const customerAddress = trip.customerLocationAddress || trip.customer_location_address || "Customer location not confirmed yet.";
  const customerLat = trip.customerLocationLat ?? trip.customer_location_lat;
  const customerLng = trip.customerLocationLng ?? trip.customer_location_lng;
  const tailorLat = trip.tailorTripLat ?? trip.tailor_trip_lat;
  const tailorLng = trip.tailorTripLng ?? trip.tailor_trip_lng;
  const tripStatus = trip.measurementTripStatus || trip.measurement_trip_status || "not_started";
  const tripStatusValue = String(tripStatus).toLowerCase();
  const verified = Boolean(trip.measurementOtpVerifiedAt || trip.measurement_otp_verified_at || tripStatusValue === "otp_verified");
  const hasTailorLiveLocation = tailorLat !== null && tailorLat !== undefined && tailorLng !== null && tailorLng !== undefined;
  const tailorLocationUrl = hasTailorLiveLocation ? mapLinkFor(tailorLat, tailorLng) : "";
  const tailorLocationTitle = hasTailorLiveLocation
    ? `${Number(tailorLat).toFixed(5)}, ${Number(tailorLng).toFixed(5)}`
    : tripStatusValue === "not_started"
      ? "Waiting for tailor to start"
      : tripStatusValue === "en_route"
        ? "Tailor started for measurement"
        : tripStatusValue === "arrived"
          ? "Tailor reached your address"
          : verified
            ? "Arrival OTP verified"
            : "Measurement visit updated";
  const tailorLocationHint = hasTailorLiveLocation
    ? ""
    : tripStatusValue === "not_started"
      ? "Live location appears after the tailor starts."
      : "Trip status updated. Live location appears after browser location permission is allowed.";
  const routeUrl = trip.tailorDirectionsUrl || trip.tailor_directions_url || mapLinkFor(customerLat, customerLng, customerAddress);

  return (
    <div className="measurement-trip-panel">
      <div className="trip-panel-head">
        <div>
          <h3>Measurement visit</h3>
          <p>Track the tailor visit and open the address in Google Maps after booking.</p>
        </div>
        <span className="trip-status-pill">{tripStatusLabel(tripStatus)}</span>
      </div>
      <div className="trip-grid">
        <div className="trip-info-card">
          <small>Your pinned address</small>
          <strong>{customerAddress}</strong>
          <a className="trip-map-link" href={routeUrl} target="_blank" rel="noreferrer">Open in Google Maps</a>
        </div>
        <div className="trip-info-card">
          <small>Tailor live location</small>
          <strong>{tailorLocationTitle}</strong>
          {tailorLocationUrl ? <a className="trip-map-link" href={tailorLocationUrl} target="_blank" rel="noreferrer">Track on map</a> : <span>{tailorLocationHint}</span>}
        </div>
        <div className="trip-info-card">
          <small>Arrival security</small>
          <strong>{verified ? "OTP verified" : "OTP required before measurement"}</strong>
          <span>Share the OTP only after the tailor reaches your address.</span>
        </div>
      </div>
      <div className="trip-info-card trip-wide-card">
        <small>Visit updates</small>
        <strong>{tripStatusValue === "not_started" ? "Tailor has not started yet" : tripStatusLabel(tripStatus)}</strong>
        <span>
          {tripStatusValue === "not_started"
            ? "You will get an in-app update when the tailor starts for measurement."
            : tripStatusValue === "en_route"
              ? "Tailor started for measurement. Please be ready at your pinned address."
              : tripStatusValue === "arrived"
                ? "Tailor reached your address. Share the arrival OTP only after confirming."
                : verified
                  ? "Arrival OTP is verified. Measurement can begin."
                  : "Your measurement visit status was updated."}
        </span>
      </div>
      {error ? <small className="field-error">{error}</small> : null}
    </div>
  );
}

function TailorMeasurementVisitPanel({ order, reload, onReadyChange }) {
  const [trip, setTrip] = useState(order);
  const [otp, setOtp] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadTrip() {
    if (!order?.id) return;
    try {
      const res = await api.measurementTrip(order.id);
      setTrip(res.booking || order);
    } catch {}
  }

  useEffect(() => {
    setTrip(order);
    loadTrip();
  }, [order?.id]);

  useBookingLiveUpdates(
    order?.id,
    (payload) => setTrip(payload?.booking || order),
    loadTrip,
    Boolean(order?.id),
  );

  useEffect(() => {
    function refreshTrip(event) {
      if (!event.detail?.bookingId || event.detail.bookingId === order?.id) loadTrip();
    }
    window.addEventListener("tailorahub:booking-trip-refresh", refreshTrip);
    return () => window.removeEventListener("tailorahub:booking-trip-refresh", refreshTrip);
  }, [order?.id]);

  const needsVisit = isTailorVisitOrder(trip);
  const tripStatus = trip.measurementTripStatus || trip.measurement_trip_status || "not_started";
  const tripStatusValue = String(tripStatus).toLowerCase();
  const verified = !needsVisit || Boolean(trip.measurementOtpVerifiedAt || trip.measurement_otp_verified_at || tripStatusValue === "otp_verified");

  useEffect(() => {
    onReadyChange?.(verified);
  }, [verified, onReadyChange]);

  useEffect(() => {
    const canAutoShare = needsVisit && ["en_route", "arrived"].includes(tripStatusValue) && !verified;
    if (!canAutoShare || !navigator.geolocation || !order?.id) return undefined;
    let lastSentAt = 0;
    const watcher = navigator.geolocation.watchPosition(
      async (position) => {
        const now = Date.now();
        if (now - lastSentAt < 15000) return;
        lastSentAt = now;
        try {
          const res = await api.updateMeasurementTripLocation(order.id, {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
          if (res.booking) setTrip(res.booking);
        } catch {}
      },
      () => {},
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 12000 }
    );
    return () => navigator.geolocation.clearWatch(watcher);
  }, [order?.id, needsVisit, tripStatusValue, verified]);

  if (!order?.id) return null;
  if (!needsVisit) return null;

  const customerAddress = trip.customerLocationAddress || trip.customer_location_address || "Customer location not confirmed.";
  const customerLat = trip.customerLocationLat ?? trip.customer_location_lat;
  const customerLng = trip.customerLocationLng ?? trip.customer_location_lng;
  const customerMapUrl = trip.customerMapUrl || trip.customer_map_url || mapLinkFor(customerLat, customerLng, customerAddress);
  const routeUrl = trip.tailorDirectionsUrl || trip.tailor_directions_url || customerMapUrl;
  const canMarkArrived = ["en_route", "arrived"].includes(tripStatusValue);
  const canVerifyOtp = ["arrived", "otp_verified"].includes(tripStatusValue) && !verified;

  async function runAction(action, { requireLocation = false } = {}) {
    setBusy(true);
    setMessage("");
    try {
      const coords = await getBrowserCoordinates({ required: requireLocation });
      const res = await action(coords);
      setTrip(res.booking || trip);
      setMessage(res.message || "Visit updated.");
      notifyBookingPanels(order.id);
      reload?.();
    } catch (err) {
      setMessage(err.message || "Visit update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyArrivalOtp() {
    if (!/^\d{6}$/.test(otp)) {
      setMessage("Enter the 6 digit OTP shared by the customer.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const res = await api.verifyMeasurementTripOtp(order.id, otp);
      setTrip(res.booking || trip);
      setOtp("");
      setMessage(res.message || "Customer arrival OTP verified. Measurement is unlocked.");
      notifyBookingPanels(order.id);
      reload?.();
    } catch (err) {
      setMessage(err.message || "OTP verification failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="measurement-trip-panel">
      <div className="trip-panel-head">
        <div>
          <h3>Customer visit tracking</h3>
          <p>Start the trip, notify the customer, verify arrival OTP, then mark measurement done.</p>
        </div>
        <span className="trip-status-pill">{tripStatusLabel(tripStatus)}</span>
      </div>
      <div className="trip-grid">
        <div className="trip-info-card">
          <small>Customer</small>
          <strong>{trip.customerName || trip.customer_name || order.customer_name}</strong>
          <span>{trip.customerPhone || trip.customer_phone || order.customer_phone || "Phone available after booking"}</span>
        </div>
        <div className="trip-info-card">
          <small>Pinned customer address</small>
          <strong>{customerAddress}</strong>
          <a className="trip-map-link" href={customerMapUrl} target="_blank" rel="noreferrer">See in Google Maps</a>
        </div>
        <div className="trip-info-card">
          <small>Secure measurement gate</small>
          <strong>{verified ? "Measurement unlocked" : "OTP verification pending"}</strong>
          <span>{verified ? "You can mark measurement done." : "Do not take measurements before OTP verification."}</span>
        </div>
      </div>
      <div className="trip-actions">
        <button type="button" onClick={() => runAction((coords) => api.startMeasurementTrip(order.id, coords), { requireLocation: true })} disabled={busy || tripStatusValue !== "not_started"}>I started from here</button>
        <button type="button" onClick={() => runAction((coords) => api.arriveMeasurementTrip(order.id, coords), { requireLocation: true })} disabled={busy || !canMarkArrived || verified}>I reached customer</button>
        <a className="trip-map-link" href={routeUrl} target="_blank" rel="noreferrer">Open route</a>
        <input value={otp} onChange={(event) => setOtp(cleanDigits(event.target.value))} inputMode="numeric" maxLength={6} placeholder="Customer OTP" disabled={busy || !canVerifyOtp} />
        <button type="button" onClick={verifyArrivalOtp} disabled={busy || !canVerifyOtp || otp.length !== 6}>Verify arrival OTP</button>
      </div>
      {message ? <small className={["verified", "sent", "updated", "unlocked", "shared", "marked", "started", "reached"].some((word) => message.toLowerCase().includes(word)) ? "field-success" : "field-error"}>{message}</small> : null}
    </div>
  );
}

function CustomerOrderCard({ order, reload }) {
  const deepLinked = new URLSearchParams(window.location.search).get("orderId") === String(order.id);
  const [statusData, setStatusData] = useState(() => normalizeOrderStatusPayload(order, null));
  const [breakdown, setBreakdown] = useState(null);
  const [paymentIntent, setPaymentIntent] = useState(order.paymentIntent || order.payment_intent || null);
  const [invoice, setInvoice] = useState(order.invoice || null);
  const [activeView, setActiveView] = useState("");
  const [detailsOpen, setDetailsOpen] = useState(deepLinked);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [paymentConfirmOpen, setPaymentConfirmOpen] = useState(false);
  const paymentRequestKeyRef = useRef(null);

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

  async function loadInvoice() {
    try {
      const response = await api.bookingInvoice(order.id);
      setInvoice(response.invoice || null);
    } catch {
      setInvoice(null);
    }
  }

  useEffect(() => {
    if (!detailsOpen) {
      setStatusData(normalizeOrderStatusPayload(order, null));
      return;
    }
    loadStatus();
    loadBreakdown();
    if (String(statusData.paymentStatus || statusData.payment_status || "").toLowerCase() === "paid") loadInvoice();
  }, [order, detailsOpen]);

  useBookingLiveUpdates(
    order.id,
    (payload) => {
      const nextStatus = normalizeOrderStatusPayload(order, payload);
      setStatusData(nextStatus);
      if (nextStatus.paymentIntent) setPaymentIntent(nextStatus.paymentIntent);
    },
    loadStatus,
    detailsOpen,
  );

  async function pay() {
    setBusy(true);
    setMessage("");
    try {
      const currentBreakdown = breakdown || await api.bookingPaymentBreakdown(order.id);
      setBreakdown(currentBreakdown);
      const idempotencyKey = paymentRequestKeyRef.current || crypto.randomUUID();
      paymentRequestKeyRef.current = idempotencyKey;
      const res = await api.payBooking(order.id, { method: "razorpay", idempotencyKey });
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
      if (verified.invoice) setInvoice(verified.invoice);
      paymentRequestKeyRef.current = null;
      if (verifiedIntent) setPaymentIntent(verifiedIntent);
      setMessage(verified.message || "Payment completed securely through Razorpay. Delivery OTP is now enabled.");
      if (res.breakdown) setBreakdown(res.breakdown);
      await loadStatus();
      await loadInvoice();
      await reload();
    } catch (err) {
      if (/expired|cancelled|already/i.test(err.message || "")) paymentRequestKeyRef.current = null;
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  function requestPayment() {
    if (!busy) setPaymentConfirmOpen(true);
  }

  async function resendInvoice() {
    setBusy(true);
    try {
      const response = await api.resendBookingInvoiceEmail(order.id);
      setInvoice(response.invoice || invoice);
      setMessage(response.message || "Invoice email queued successfully.");
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
  const deliveryDate = statusData.expectedCompletion || statusData.expected_completion;
  const blockedReason = statusData.customerManageBlockedReason || statusData.customer_manage_blocked_reason || "Manage options close on the measurement appointment date.";
  const displayStatus = cancelled ? "CANCELLED" : completed ? "COMPLETED" : currentStep.stage || statusData.status;

  return (
    <article id={`order-${order.id}`} className={`${completed ? "compact-order-card customer-order-card completed" : cancelled ? "compact-order-card customer-order-card cancelled" : "compact-order-card customer-order-card"}${detailsOpen ? " details-open" : ""}${deepLinked ? " deep-linked" : ""}`}>
      <div className="customer-order-preview">
        <div className="customer-order-primary">
          <small>{statusData.code || order.code}</small>
          <h3>{statusData.serviceName || order.service_name}</h3>
          <p>Tailor: {statusData.tailorName || order.shop}</p>
          {String(statusData.status || "").toUpperCase() === "PENDING_APPROVAL" ? <ExpiryCountdown expiresAt={statusData.expiresAt || statusData.expires_at} /> : null}
        </div>
        <div className="customer-order-stage"><StatusPill value={displayStatus} /></div>
        <div className="customer-order-facts">
          <span><FileClock size={15} /><small>Due {fmtDay(deliveryDate)}</small></span>
          <span><CreditCard size={15} /><small>{money(statusData.total || order.total)}</small></span>
          <span><Scissors size={15} /><small>{currentStep.stage || "Tracked order"}</small></span>
        </div>
        <div className="customer-order-reference-actions">
          <button
            type="button"
            className={detailsOpen && activeView === "track" ? "secondary-btn active" : "secondary-btn"}
            onClick={() => {
              setDetailsOpen(true);
              setActiveView((view) => view === "track" ? "" : "track");
            }}
          >
            {detailsOpen && activeView === "track" ? "Hide timeline" : "View timeline"}
          </button>
          <button
            type="button"
            className="primary-btn"
            onClick={() => {
              setDetailsOpen((open) => !open);
              setActiveView("");
            }}
          >
            {detailsOpen ? "Close order" : "Open order"} <ArrowRight size={17} />
          </button>
        </div>
        <div className="customer-order-progress compact-progress-row" aria-label={`Order progress ${progress}%`}>
          <span><i style={{ width: `${progress}%` }} /></span>
        </div>
      </div>

      {detailsOpen ? (
        <div className="compact-order-actions customer-order-expanded-actions" role="tablist" aria-label={`Actions for ${statusData.code || order.code}`}>
          {!completed && !cancelled ? (
            <>
              <button type="button" className={activeView === "manage" ? "active" : ""} onClick={() => setActiveView((view) => view === "manage" ? "" : "manage")} disabled={!manageable}>
                Manage order
              </button>
              <button type="button" className={activeView === "instructions" ? "active" : ""} onClick={() => setActiveView((view) => view === "instructions" ? "" : "instructions")} disabled={!manageable}>
                Update instructions
              </button>
              {isTailorVisitOrder(statusData) ? (
                <button type="button" className={activeView === "measurement" ? "active" : ""} onClick={() => setActiveView((view) => view === "measurement" ? "" : "measurement")}>
                  Measurement visit
                </button>
              ) : null}
            </>
          ) : null}
          {!isPaid && !completed && !cancelled ? <button type="button" onClick={requestPayment} disabled={busy}>{busy ? "Opening..." : "Pay securely"}</button> : null}
          {completed ? <button type="button" className={activeView === "feedback" ? "active" : ""} onClick={() => setActiveView((view) => view === "feedback" ? "" : "feedback")}>Feedback</button> : null}
          <StatusPill value={statusData.paymentStatus || statusData.payment_status} />
        </div>
      ) : null}

      {detailsOpen && !manageable && !completed && !cancelled ? <small className="manage-cutoff-note">{blockedReason}</small> : null}
      {cancelled ? <div className="notice">Order cancelled: {statusData.cancelReason || statusData.cancel_reason || "Cancelled before measurement."}</div> : null}

      {detailsOpen && statusData.contactSharingActive ? (
        <div className="compact-order-panel booking-contact-panel">
          <h3>Confirmed tailor contact</h3>
          <p><strong>{statusData.tailorName || order.shop}</strong>{statusData.tailorOwnerName ? ` - ${statusData.tailorOwnerName}` : ""}</p>
          {statusData.tailorPhone ? <a className="secondary-btn" href={`tel:${statusData.tailorPhone}`}>Call {statusData.tailorPhone}</a> : <small>Tailor phone number is not available.</small>}
          <p>{statusData.tailorLocationAddress || "Shop address is not available."}</p>
          {statusData.tailorMapUrl ? <a className="secondary-btn" href={statusData.tailorMapUrl} target="_blank" rel="noreferrer">Open shop location</a> : null}
          {statusData.tailorDirectionsUrl ? <a className="secondary-btn" href={statusData.tailorDirectionsUrl} target="_blank" rel="noreferrer">Get directions</a> : null}
        </div>
      ) : null}

      {detailsOpen && activeView === "track" ? (
        <div className="compact-order-panel">
          <OrderTracker steps={statusData.steps} />
          {completed ? <QualityCheckPrompt onDispute={raiseDispute} busy={busy} /> : null}
        </div>
      ) : null}

      {detailsOpen && activeView === "measurement" && !completed && !cancelled ? (
        <div className="compact-order-panel customer-measurement-panel">
          <CustomerMeasurementVisitPanel order={statusData} />
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
      {invoice ? (
        <div className="notice ok payment-success-invoice">
          <strong>Payment successful</strong>
          <span>Your booking is confirmed and invoice {invoice.invoice_number || invoice.invoiceNumber} is available.</span>
          {(invoice.download_url || invoice.downloadUrl) ? <a className="secondary-btn" href={invoice.download_url || invoice.downloadUrl} target="_blank" rel="noreferrer">View invoice PDF</a> : null}
          {invoice.email_status === "failed" ? <button type="button" className="secondary-btn" onClick={resendInvoice} disabled={busy}>Retry invoice email</button> : null}
        </div>
      ) : null}
      <ExternalPaymentConfirmDialog
        open={paymentConfirmOpen}
        busy={busy}
        onCancel={() => setPaymentConfirmOpen(false)}
        onConfirm={() => { setPaymentConfirmOpen(false); pay(); }}
      />
    </article>
  );
}

function CustomerOrderManagePanel({ order, busy, mode, onUpdate, onCancel }) {
  const [deliveryDate, setDeliveryDate] = useState(orderDateInput(order.expectedCompletion || order.expected_completion));
  const [instructions, setInstructions] = useState(order.notes || "");
  const [cancelReason, setCancelReason] = useState("");
  const [localError, setLocalError] = useState("");
  const appointmentDate = orderDateInput(order.appointmentDate || order.appointment_date);
  const minFromAppointment = appointmentDate;
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
      setLocalError("Delivery date cannot be before the measurement appointment.");
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
      {gatewayOrderId ? <small>Your secure payment request is ready.</small> : null}
    </div>
  );
}

function PaymentBreakdownCard({ breakdown }) {
  if (!breakdown) {
    return <div className="payment-breakdown"><small>Loading payment breakdown...</small></div>;
  }
  const orderAmount = breakdown.orderAmount ?? breakdown.order_amount;
  const serviceAmount = breakdown.serviceAmount ?? breakdown.service_amount ?? orderAmount;
  const urgentCharge = breakdown.urgentCharge ?? breakdown.urgent_charge ?? 0;
  const payableTotal = breakdown.payableTotal ?? breakdown.payable_total;
  return (
    <div className="payment-breakdown">
      <div><span>Service amount</span><strong>{money(serviceAmount)}</strong></div>
      {Number(urgentCharge) > 0 ? <div><span>Urgent completion charge</span><strong>{money(urgentCharge)}</strong></div> : null}
      <div><span>Booking total</span><strong>{money(orderAmount)}</strong></div>
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
  const { language, setLanguage } = useLanguage();
  const [data, setData] = useState(null);
  const [availability, setAvailability] = useState({});
  const [savedAvailability, setSavedAvailability] = useState({});
  const [availabilityFeedback, setAvailabilityFeedback] = useState("");
  const [savingAvailability, setSavingAvailability] = useState(false);
  const [activePanel, setActivePanel] = useAppHistoryState("tailorPanel", "overview");
  const [workspaceSearch, setWorkspaceSearch] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const next = await api.tailorDashboard();
      setData(next);
      const nextAvailability = {
        availability: next.tailor.availability || "AVAILABLE",
        availableSlots: next.tailor.availableSlots || 0,
        maxNewOrders: next.tailor.maxNewOrders || 0,
        nextAvailable: next.tailor.nextAvailable || "",
        availabilityNote: next.tailor.availabilityNote || "",
        acceptingRequests: next.tailor.acceptingRequests,
        approvalMode: next.tailor.approvalMode || "AUTOMATIC",
      };
      setAvailability(nextAvailability);
      setSavedAvailability(nextAvailability);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, []);
  useAutoRefresh(load);

  async function saveAvailability(event) {
    event.preventDefault();
    const payload = { ...availability, nextAvailable: availability.nextAvailable || null };
    const savedPayload = { ...savedAvailability, nextAvailable: savedAvailability.nextAvailable || null };
    if (JSON.stringify(payload) === JSON.stringify(savedPayload)) {
      setAvailabilityFeedback("No changes to save.");
      return;
    }
    setSavingAvailability(true);
    setAvailabilityFeedback("");
    try {
      await api.updateAvailability(payload);
      await load();
      setAvailabilityFeedback("Availability changes saved successfully.");
    } catch (err) {
      setAvailabilityFeedback(err.message || "Unable to save availability changes.");
    } finally {
      setSavingAvailability(false);
    }
  }

  const unreadUpdates = unreadCount(data?.notifications || []);

  async function openTailorNotification(row) {
    await api.markTailorNotificationRead(row.id);
    setData((old) => old ? { ...old, notifications: (old.notifications || []).map((item) => item.id === row.id ? { ...item, read: true, read_at: new Date().toISOString() } : item) } : old);
    const entityId = row.entity_id || row.order_id || row.booking_request_id;
    const entityType = String(row.entity_type || "booking").toLowerCase();
    setActivePanel(entityType === "request" || entityType === "booking_request" ? "requests" : "orders");
    const url = new URL(window.location.href);
    if (entityId) url.searchParams.set(entityType.includes("request") ? "requestId" : "orderId", entityId);
    window.history.replaceState(currentHistoryState(), "", `${url.pathname}${url.search}${url.hash}`);
  }

  if (!data) return <Shell title={t("dashboard.tailor.title", "Tailor Dashboard")} subtitle={t("dashboard.tailor.subtitle", "Requests, orders and availability")} icon={Scissors} onLogout={onLogout}>{error ? <div className="error banner">{error}</div> : <div className="loading">{t("tailor.loading", "Loading tailor dashboard...")}</div>}</Shell>;
  const pendingApproval = data.tailor.approvalStatus !== "APPROVED";
  const mediaCount = portfolioItems(data.tailor.portfolio).length;
  const activeOffers = (data.offers || []).filter((offer) => offer.active !== false).length;
  const tailorInitials = String(data.tailor.shop || data.tailor.ownerName || "Tailor").trim().split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "TH";
  const panels = [
    ["overview", t("common.overview", "Overview"), LayoutDashboard, null],
    ["profile", "Atelier profile", BadgeCheck, null],
    ["availability", t("common.availability", "Availability"), CheckCircle2, null],
    ["requests", "Booking requests", ClipboardList, Number(data.stats.pending_requests || 0)],
    ["waiting", t("common.waitingList", "Waiting list"), FileClock, Number(data.stats.waiting_list || data.stats.waitlisted || 0)],
    ["orders", "Order queue", Scissors, Number(data.stats.active_orders || 0)],
    ["services", "Services & pricing", Tag, null],
    ["media", "Portfolio", ImageIcon, mediaCount],
    ["offers", t("common.offers", "Offers"), Megaphone, null],
    ["followers", t("common.followers", "Followers"), UsersRound, null],
    ["wallet", "Earnings & wallet", CreditCard, null],
    ["referrals", t("common.referrals", "Referrals"), UsersRound, null],
    ["updates", t("common.updates", "Updates"), FileClock, unreadUpdates],
    ["support", t("common.support", "Support"), AlertTriangle, null],
  ];
  const mobilePanels = ["overview", "availability", "requests", "orders", "wallet"]
    .map((id) => panels.find((panel) => panel[0] === id))
    .filter(Boolean)
    .map((panel) => panel[0] === "orders" ? [panel[0], "Orders", panel[2], panel[3]] : panel);
  const mobileTitle = panels.find((panel) => panel[0] === activePanel)?.[1] || "Tailor workspace";
  const selectTailorPanel = (id) => {
    setActivePanel(id);
    setMobileMenuOpen(false);
  };

  return (
    <Shell
      variant="tailor"
      title={data.tailor.shop}
      subtitle={t("dashboard.tailor.title", "Tailor Dashboard")}
      icon={Scissors}
      onLogout={onLogout}
      searchValue={workspaceSearch}
      onSearch={setWorkspaceSearch}
      onUpdates={() => selectTailorPanel("updates")}
      avatarLabel={tailorInitials}
      unread={unreadUpdates}
      mobileTitle={mobileTitle}
      onMobileMenu={() => setMobileMenuOpen((open) => !open)}
      mobileMenuOpen={mobileMenuOpen}
    >
      <div className="tailor-workspace customer-workspace">
        {mobileMenuOpen ? <button type="button" className="workspace-mobile-backdrop" onClick={() => setMobileMenuOpen(false)} aria-label="Close workspace navigation" /> : null}
        <aside className={`tailor-side-card customer-side-card ${mobileMenuOpen ? "mobile-open" : ""}`}>
          <RoleSidebarBrand role="tailor" screenCount={panels.length} />
          <nav className="tailor-side-nav">
            {panels.map(([id, label, Icon, count]) => (
              <button key={id} className={activePanel === id ? "active" : ""} onClick={() => selectTailorPanel(id)}>
                <Icon size={16} />
                <span>{label}</span>
                {count ? <b>{count}</b> : null}
              </button>
            ))}
          </nav>
          <div className="customer-sidebar-footer">
            <div className="customer-sidebar-tools">
              <LanguageSelect language={language} setLanguage={setLanguage} />
              <button className="icon-btn" onClick={load} title={t("common.refresh", "Refresh")}><RefreshCw size={17} /></button>
              <button className="icon-btn" onClick={onLogout} title={t("common.logout", "Logout")}><LogOut size={17} /></button>
            </div>
            <div className="customer-sidebar-user">
              <TailorAvatar tailor={data.tailor} size="md" />
              <span><strong>{data.tailor.shop}</strong><small>{data.tailor.ownerName}</small></span>
            </div>
          </div>
        </aside>
        <WorkspaceMobileNav panels={mobilePanels} activePanel={activePanel} onSelect={selectTailorPanel} />
        <div className="tailor-content customer-content">
          {error ? <div className="error banner">{error}</div> : null}
          {pendingApproval ? <div className="notice warn">{t("tailor.profilePending", `Your tailor profile is ${data.tailor.approvalStatus}. Customers will see you only after admin approval.`, { status: data.tailor.approvalStatus })}</div> : null}
          <WorkspacePageHeading role="tailor" panelId={activePanel} label={mobileTitle} />
          {activePanel === "overview" ? <TailorOverviewPanel data={data} onNavigate={setActivePanel} /> : null}
          {activePanel === "profile" ? <TailorProfilePanel tailor={data.tailor} onNavigate={setActivePanel} /> : null}
          {activePanel === "availability" ? <TailorAvailabilityPanel availability={availability} setAvailability={(next) => { setAvailability(next); setAvailabilityFeedback(""); }} saveAvailability={saveAvailability} feedback={availabilityFeedback} saving={savingAvailability} /> : null}
          {activePanel === "wallet" ? <TailorWalletPanel /> : null}
          {activePanel === "referrals" ? <TailorReferralPanel /> : null}
          {activePanel === "media" ? <TailorMediaPanel tailor={data.tailor} reload={load} /> : null}
          {activePanel === "services" ? <TailorServicesPanel /> : null}
          {activePanel === "offers" ? <TailorOffersPanel offers={data.offers || []} reload={load} /> : null}
          {activePanel === "followers" ? <TailorFollowersPanel followers={data.followers || []} /> : null}
          {activePanel === "requests" ? <TailorRequests rows={data.requests} reload={load} /> : null}
          {activePanel === "waiting" ? <TailorWaitingListPanel reloadDashboard={load} /> : null}
          {activePanel === "orders" ? <TailorOrders rows={data.orders} reload={load} /> : null}
          {activePanel === "updates" ? <Updates title={t("tailor.updatesTitle", "Tailor Updates")} rows={data.notifications || []} onOpen={openTailorNotification} /> : null}
          {activePanel === "support" ? <SupportPanel role="tailor" orders={data.orders || []} /> : null}
        </div>
      </div>
    </Shell>
  );
}

function TailorOverviewPanel({ data, onNavigate }) {
  const pendingRequests = (data.requests || []).filter((row) => String(row.status || "").toUpperCase() === "PENDING");
  const activeOrders = (data.orders || []).filter((row) => !["DELIVERED", "COMPLETED", "CANCELLED", "REJECTED"].includes(String(row.status || "").toUpperCase()));
  const priority = pendingRequests[0] || activeOrders[0] || null;
  const priorityIsRequest = Boolean(priority && pendingRequests.includes(priority));
  const recentUpdates = (data.notifications || []).slice(0, 3);
  const availableSlots = Number(data.tailor.availableSlots || 0);
  return (
    <section className="tailor-approved-overview">
      <header className="customer-page-heading tailor-page-heading">
        <div>
          <span className="customer-page-eyebrow">Tailor workspace</span>
          <h1>Overview</h1>
          <p>Today&apos;s workboard brings requests, due orders and earnings into focus.</p>
        </div>
      </header>
      <div className="tailor-overview-kpis">
        <article><ClipboardList size={24} /><span><small>New requests</small><strong>{String(data.stats.pending_requests || 0).padStart(2, "0")}</strong><em>{pendingRequests.length ? `${pendingRequests.length} need attention` : "Nothing pending"}</em></span></article>
        <article><Scissors size={24} /><span><small>Active orders</small><strong>{String(data.stats.active_orders || 0).padStart(2, "0")}</strong><em>{activeOrders.length ? "Work currently in progress" : "Queue is clear"}</em></span></article>
        <article><FileClock size={24} /><span><small>Available slots</small><strong>{String(availableSlots).padStart(2, "0")}/{String(APPOINTMENT_TIME_SLOTS.length).padStart(2, "0")}</strong><em>{data.tailor.acceptingRequests ? "Accepting bookings" : "Requests paused"}</em></span></article>
        <article><CreditCard size={24} /><span><small>Total earnings</small><strong>{money(data.stats.earnings || 0)}</strong><em>Live wallet total</em></span></article>
      </div>
      <div className="tailor-overview-focus-grid">
        <section className="tailor-workboard-card">
          <div className="tailor-panel-heading">
            <div><span>Priority</span><h2>Today&apos;s workboard</h2></div>
            <button type="button" onClick={() => onNavigate(priorityIsRequest ? "requests" : "orders")}>View details <ArrowRight size={17} /></button>
          </div>
          {priority ? (
            <article className="tailor-priority-row">
              <div className="tailor-priority-date"><small>{fmtDay(priority.preferred_date || priority.measurement_date || priority.delivery_date || priority.ts)}</small></div>
              <div className="tailor-priority-copy">
                <StatusPill value={priority.status || (priorityIsRequest ? "PENDING" : "IN_PROGRESS")} />
                <strong>{priorityIsRequest ? (priority.tailor_service_name || priority.service_name || "Booking request") : (priority.serviceName || priority.service_name || priority.code || "Active order")}</strong>
                <span>{priorityIsRequest ? (priority.customer_name || priority.customer_area || "Customer request") : `${priority.code || priority.id || "Order"} · ${priority.customerName || priority.customer_name || "Customer"}`}</span>
              </div>
              <button type="button" className="primary-btn" onClick={() => onNavigate(priorityIsRequest ? "requests" : "orders")}>Open details <ArrowRight size={16} /></button>
            </article>
          ) : <Empty text="No priority requests or active orders right now." />}
          <div className="tailor-workboard-progress" aria-label="Tailor workflow">
            {["Booked", "Measured", "In progress", "Final fitting"].map((label, index) => <span key={label} className={index === 0 || activeOrders.length ? "done" : ""}><b>{index < 3 && activeOrders.length ? "✓" : index + 1}</b><small>{label}</small></span>)}
          </div>
        </section>
        <aside className="tailor-concierge-card">
          <span className="tailor-concierge-icon"><AlertTriangle size={24} /></span>
          <small>TailoraHub concierge</small>
          <h2>Need a little help?</h2>
          <p>Support stays connected to the relevant booking, order or payment.</p>
          <button type="button" onClick={() => onNavigate("support")}>Start a conversation <ArrowRight size={17} /></button>
        </aside>
      </div>
      <section className="tailor-recent-updates">
        <div className="tailor-panel-heading">
          <div><span>Live activity</span><h2>Recent updates</h2></div>
          <button type="button" onClick={() => onNavigate("updates")}>View all <ArrowRight size={17} /></button>
        </div>
        {recentUpdates.length ? (
          <div className="tailor-updates-table">
            <div className="tailor-updates-head"><span>Item</span><span>Details</span><span>Updated</span><span>Status</span></div>
            {recentUpdates.map((row) => (
              <button type="button" key={row.id} onClick={() => onNavigate("updates")}>
                <strong>{row.entity_id || row.order_id || row.booking_request_id || "Update"}</strong>
                <span>{row.title || row.body || "TailoraHub update"}</span>
                <span>{fmtDate(row.ts)}</span>
                <StatusPill value={updatePresentation(row).status} />
              </button>
            ))}
          </div>
        ) : <Empty text="No recent updates." />}
      </section>
    </section>
  );
}

function TailorAvailabilityPanel({ availability, setAvailability, saveAvailability, feedback, saving }) {
  const t = useT();
  const [slotDate, setSlotDate] = useState(todayDateInput());
  const [slots, setSlots] = useState(() => APPOINTMENT_TIME_SLOTS.map((slot) => ({ slot: slot.value, enabled: true, capacity: 1, bookedCount: 0 })));
  const [slotMessage, setSlotMessage] = useState("");

  useEffect(() => {
    if (availability.approvalMode !== "AUTOMATIC" || !slotDate) return;
    api.tailorSlotCapacities(slotDate).then((result) => {
      const existing = new Map((result.slots || []).map((row) => [row.slot_value || row.slot, row]));
      setSlots(APPOINTMENT_TIME_SLOTS.map((slot) => {
        const row = existing.get(slot.value);
        return { slot: slot.value, enabled: row ? Boolean(row.enabled) : true, capacity: Number(row?.capacity || 1), bookedCount: Number(row?.booked_count || 0) };
      }));
    }).catch((err) => setSlotMessage(err.message));
  }, [availability.approvalMode, slotDate]);

  async function saveSlots() {
    setSlotMessage("");
    try {
      await api.saveTailorSlotCapacities({ date: slotDate, slots: slots.map(({ slot, enabled, capacity }) => ({ slot, enabled, capacity })) });
      setSlotMessage("Slot capacities saved.");
    } catch (err) {
      setSlotMessage(err.message);
    }
  }
  const statusOptions = [
    ["AVAILABLE", "Available", "Accepting new booking requests", "#4aa178"],
    ["FEW_SLOTS_AVAILABLE", "Few slots", "Limited booking capacity", "#d79a29"],
    ["BUSY", "Busy", "Requests may be delayed", "#918b82"],
    ["NOT_AVAILABLE", "Not available", "Pause new requests", "#c85a57"],
  ];
  return (
    <section className="tailor-approved-availability">
      <header className="customer-page-heading tailor-page-heading">
        <div>
          <span className="customer-page-eyebrow">Tailor workspace</span>
          <h1>{t("common.availability", "Availability")}</h1>
          <p>Control booking mode, slot capacity and working hours with confidence.</p>
        </div>
        <button type="submit" form="tailor-availability-form" className="primary-btn customer-heading-action" disabled={saving}>{saving ? "Saving..." : "Save availability"} <ArrowRight size={17} /></button>
      </header>
      <div className="tailor-status-selector" role="group" aria-label="Availability status">
        {statusOptions.map(([value, label, description, color]) => (
          <button type="button" key={value} className={availability.availability === value ? "active" : ""} onClick={() => setAvailability({ ...availability, availability: value })}>
            <span className="tailor-status-dot" style={{ backgroundColor: color }} />
            <strong>{label}</strong>
            <small>{description}</small>
            {availability.availability === value ? <CheckCircle2 size={17} /> : null}
          </button>
        ))}
      </div>
      <form id="tailor-availability-form" className="availability-form tailor-availability-settings" onSubmit={saveAvailability}>
        <div className="tailor-panel-heading span-2"><div><span>Booking settings</span><h2>Request controls</h2></div></div>
        <label>Approval mode<select value={availability.approvalMode || "AUTOMATIC"} onChange={(e) => setAvailability({ ...availability, approvalMode: e.target.value })}><option value="AUTOMATIC">Automatic Approval</option><option value="MANUAL">Manual Approval</option></select></label>
        <label>{t("tailor.nextAvailableDate", "Next available date")}<input type="date" min={todayDateInput()} value={availability.nextAvailable || ""} onChange={(e) => setAvailability({ ...availability, nextAvailable: e.target.value })} /></label>
        {availability.approvalMode === "AUTOMATIC" ? <><label>{t("tailor.availableSlots", "Default slot capacity")}<input type="number" min="0" value={availability.availableSlots} onChange={(e) => setAvailability({ ...availability, availableSlots: Number(e.target.value) })} /></label><label>{t("tailor.maxNewOrders", "Max new orders")}<input type="number" min="0" value={availability.maxNewOrders} onChange={(e) => setAvailability({ ...availability, maxNewOrders: Number(e.target.value) })} /></label></> : <div className="notice span-2">Manual requests remain pending for one hour and require your approval.</div>}
        <label className="check-row tailor-accepting-toggle"><input type="checkbox" checked={Boolean(availability.acceptingRequests)} onChange={(e) => setAvailability({ ...availability, acceptingRequests: e.target.checked })} /> {t("tailor.acceptingRequests", "Accepting new requests")}</label>
        <label className="span-2">{t("tailor.availabilityNote", "Availability note")}<textarea value={availability.availabilityNote} onChange={(e) => setAvailability({ ...availability, availabilityNote: e.target.value })} /></label>
        {feedback ? <div className={feedback.includes("successfully") ? "notice ok span-2" : feedback === "No changes to save." ? "notice span-2" : "error span-2"} role="status" aria-live="polite">{feedback}</div> : null}
      </form>
      {availability.approvalMode === "AUTOMATIC" ? (
        <section className="slot-capacity-panel tailor-slot-capacity">
          <div className="tailor-panel-heading">
            <div><span>Booking capacity</span><h2>{new Date(`${slotDate}T12:00:00`).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}</h2></div>
            <label className="tailor-slot-date"><FileClock size={16} /><span>Edit date</span><input type="date" min={todayDateInput()} value={slotDate} onChange={(e) => setSlotDate(e.target.value)} /></label>
          </div>
          <div className="tailor-slot-grid">
            {slots.map((row, index) => (
              <article className={row.enabled ? "tailor-slot-card" : "tailor-slot-card disabled"} key={row.slot}>
                <div><FileClock size={17} /><strong>{APPOINTMENT_TIME_SLOTS.find((slot) => slot.value === row.slot)?.label}</strong></div>
                <small>{row.enabled ? `${row.bookedCount} of ${row.capacity} booked` : "Unavailable"}</small>
                <span><i style={{ width: `${Math.min(100, row.capacity ? (row.bookedCount / row.capacity) * 100 : 0)}%` }} /></span>
                <div className="tailor-slot-controls">
                  <label><input type="checkbox" checked={row.enabled} onChange={(e) => setSlots((old) => old.map((item, itemIndex) => itemIndex === index ? { ...item, enabled: e.target.checked } : item))} /> Enabled</label>
                  <label>Capacity <input type="number" min={row.bookedCount} max="100" value={row.capacity} disabled={!row.enabled} onChange={(e) => setSlots((old) => old.map((item, itemIndex) => itemIndex === index ? { ...item, capacity: Number(e.target.value) } : item))} /></label>
                </div>
              </article>
            ))}
          </div>
          <div className="tailor-slot-actions"><button type="button" className="primary-btn" onClick={saveSlots}>Save slot capacity</button>{slotMessage ? <div className={slotMessage.includes("saved") ? "notice ok" : "error"}>{slotMessage}</div> : null}</div>
        </section>
      ) : null}
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
      setMessage(`Withdrawal OTP sent to ${res.target || "your registered contact"}.`);
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
            {wallet?.qr_code_url ? <img src={assetUrl(wallet.qr_code_url)} alt="Wallet payment QR" loading="lazy" decoding="async" /> : <span>No QR yet</span>}
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
      const upload = await api.presignTailorProfileImage({ name: file.name, mediaType: file.type, sizeBytes: file.size });
      if (upload.mode === "direct") {
        await uploadToPresignedPost(upload, file);
        await api.completeTailorProfileImage({ name: file.name, mediaType: file.type, objectKey: upload.objectKey });
      } else {
        const dataUrl = await readFileAsDataUrl(file);
        await api.uploadTailorProfileImage({ name: file.name, mediaType: file.type, dataUrl });
      }
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
        const upload = await api.presignTailorMedia({ name: file.name, mediaType: file.type, sizeBytes: file.size });
        if (upload.mode === "direct") {
          await uploadToPresignedPost(upload, file);
          await api.completeTailorMedia({ name: file.name, mediaType: file.type, objectKey: upload.objectKey });
        } else {
          const dataUrl = await readFileAsDataUrl(file);
          await api.uploadTailorMedia({ name: file.name, mediaType: file.type, dataUrl });
        }
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
    <section className="section-block no-top tailor-offers-section">
      <div className="section-head">
        <div>
          <h3>Offers</h3>
          <p>Followers receive an in-app update when you post a new offer.</p>
        </div>
      </div>
      <form className="offer-form tailor-offer-form" onSubmit={submit}>
        <label className="offer-title-field">Offer title<input value={form.title} onChange={(e) => update("title", e.target.value)} placeholder="Festival blouse stitching offer" required /></label>
        <label className="offer-label-field">Discount / label<input value={form.discount} onChange={(e) => update("discount", e.target.value)} placeholder="10% off this week" /></label>
        <label className="offer-details-field">Offer details<textarea value={form.body} onChange={(e) => update("body", e.target.value)} placeholder="What can customers book?" required /></label>
        <label className="offer-date-field">Valid until<input type="date" value={form.expiresAt} onChange={(e) => update("expiresAt", e.target.value)} /></label>
        <label className="offer-media-field">Photo or video<input type="file" accept="image/*,video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label>
        <button className="primary-btn offer-submit" disabled={busy}>{busy ? "Posting..." : "Post Offer"}</button>
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
    if (service.isActive && !window.confirm("Deactivate this service? Customers will no longer be able to book it.")) return;
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
    <section className="section-block no-top tailor-services-section">
      <div className="section-head">
        <div>
          <h3>Services</h3>
          <p>What you stitch and at what price -- shown on your public profile before a customer books.</p>
        </div>
      </div>
      <form className="offer-form tailor-service-form" onSubmit={submit}>
        <div className="span-2 form-subhead">
          <strong>{editingId ? "Edit Service" : "Add Service"}</strong>
          {editingId ? <button type="button" className="secondary-btn" onClick={resetForm} disabled={busy}>Cancel Edit</button> : null}
        </div>
        <label className="service-name-field">Service name<input value={form.serviceName} onChange={(e) => update("serviceName", e.target.value)} placeholder="Blouse Stitching" required /></label>
        <label className="service-category-field">
          Category
          <select value={form.category} onChange={(e) => update("category", e.target.value)}>
            {SERVICE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="service-price-field">Price (Rs.)<input type="number" min="1" value={form.price} onChange={(e) => update("price", e.target.value)} required /></label>
        <label className="check-row service-combo-field">
          <input type="checkbox" checked={form.isCombo} onChange={(e) => update("isCombo", e.target.checked)} />
          This is a combo
        </label>
        {form.isCombo ? (
          <label className="span-2 service-combo-items-field">Combo items (comma separated)<input value={form.comboItems} onChange={(e) => update("comboItems", e.target.value)} placeholder="Blouse, Petticoat" /></label>
        ) : null}
        <label className="span-2 service-description-field">Description<textarea value={form.description} onChange={(e) => update("description", e.target.value)} placeholder="Short service description" /></label>
        <button className="primary-btn service-submit" disabled={busy}>{busy ? "Saving..." : editingId ? "Save Changes" : "Add Service"}</button>
      </form>
      {message ? <div className={/(added|updated|reactivated|deactivated)/i.test(message) ? "notice ok" : "error"}>{message}</div> : null}
      {loading ? (
        <Empty text="Loading services..." />
      ) : services.length ? (
        <PaginatedCards
          items={services}
          pageSize={5}
          className="record-list tailor-service-list"
          label="services"
          renderItem={(service) => (
            <article className="record-card service-row tailor-service-card">
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

function updatePresentation(row = {}) {
  const text = `${row.title || ""} ${row.body || ""}`.toLowerCase();

  if (text.includes("payment") || text.includes("razorpay") || text.includes("checkout")) {
    return { Icon: CreditCard, status: text.includes("received") || text.includes("paid") ? "PAID" : "PAYMENT" };
  }
  if (text.includes("confirm") || text.includes("approved") || text.includes("accepted")) {
    return { Icon: CheckCircle2, status: "CONFIRMED" };
  }
  if (text.includes("waiting") || text.includes("pending")) {
    return { Icon: FileClock, status: "PENDING" };
  }
  if (text.includes("otp") || text.includes("secure")) {
    return { Icon: Shield, status: "SECURE" };
  }
  if (text.includes("cancel") || text.includes("reject") || text.includes("failed")) {
    return { Icon: XCircle, status: "ACTION NEEDED" };
  }
  return { Icon: Bell, status: "IN PROGRESS" };
}

function Updates({ title, rows, onOpen }) {
  const displayTitle = String(title || "Updates").replace(/^Customer\s+/i, "");

  return (
    <section className="section-block updates-panel">
      <div className="updates-heading">
        <h3>{displayTitle}</h3>
        <p>A single timeline for booking, payment, OTP and order notifications.</p>
      </div>
      <ViewMoreGrid
        items={rows}
        initial={5}
        step={5}
        className="updates-list updates-timeline-list"
        label="updates"
        emptyText="No updates yet."
        renderItem={(row) => {
          const { Icon, status } = updatePresentation(row);
          return (
            <button
              type="button"
              className={`update-item update-action update-timeline-item ${row.read ? "read" : "unread"}`}
              onClick={() => onOpen?.(row)}
            >
              <span className="update-timeline-icon" aria-hidden="true"><Icon size={20} strokeWidth={1.8} /></span>
              <span className="update-timeline-copy">
                <strong>{row.title}</strong>
                <span>{row.body}</span>
                <small>{fmtDate(row.ts)}</small>
              </span>
              <StatusPill value={status} />
            </button>
          );
        }}
      />
    </section>
  );
}

function TailorRequests({ rows, reload }) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [workingId, setWorkingId] = useState("");
  const [message, setMessage] = useState("");
  const pending = rows.filter((r) => String(r.status || "").toUpperCase() === "PENDING");
  const completed = rows.filter((r) => ["ACCEPTED", "CONFIRMED", "REJECTED", "CLOSED", "COMPLETED"].includes(String(r.status || "").toUpperCase()));
  const normalizedQuery = query.trim().toLowerCase();
  const filteredRows = rows.filter((row) => {
    const status = String(row.status || "").toUpperCase();
    if (statusFilter !== "ALL" && status !== statusFilter) return false;
    if (!normalizedQuery) return true;
    return [row.requirement_code, row.customer_name, row.customer_area, row.tailor_service_name, row.service_name, row.measurement_mode]
      .some((value) => String(value || "").toLowerCase().includes(normalizedQuery));
  });
  const completionRate = rows.length ? Math.round((completed.length / rows.length) * 100) : 0;

  async function accept(row) {
    if (!window.confirm("Accept this request and create an order?")) return;
    setWorkingId(row.id);
    setMessage("");
    try {
      await api.acceptRequest(row.id);
      setMessage("Booking request accepted successfully.");
      await reload();
    } catch (err) {
      setMessage(err.message || "Unable to accept this request.");
    } finally {
      setWorkingId("");
    }
  }

  async function reject(row) {
    if (!window.confirm("Reject this booking request?")) return;
    const reason = window.prompt("Reject reason:", "Cannot take this order now") || "Rejected by tailor";
    setWorkingId(row.id);
    setMessage("");
    try {
      await api.rejectRequest(row.id, reason);
      setMessage("Booking request rejected.");
      await reload();
    } catch (err) {
      setMessage(err.message || "Unable to reject this request.");
    } finally {
      setWorkingId("");
    }
  }

  function exportRequests() {
    const escapeCsv = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const header = ["Request", "Customer", "Area", "Service", "Quantity", "Preferred date", "Measurement", "Status"];
    const body = filteredRows.map((row) => [
      row.requirement_code,
      row.customer_name,
      row.customer_area,
      row.tailor_service_name || row.service_name,
      row.quantity,
      row.preferred_date,
      row.measurement_mode,
      row.status,
    ]);
    const blob = new Blob([[header, ...body].map((line) => line.map(escapeCsv).join(",")).join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `tailorahub-booking-requests-${todayDateInput()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="tailor-approved-requests">
      <header className="customer-page-heading tailor-page-heading">
        <div>
          <span className="customer-page-eyebrow">Tailor workspace</span>
          <h1>Booking requests</h1>
          <p>Review new customer requests and respond before their approval window closes.</p>
        </div>
        <button type="button" className="primary-btn customer-heading-action" disabled={!pending.length} onClick={() => document.getElementById("tailor-request-records")?.scrollIntoView({ behavior: "smooth", block: "start" })}>Review next request <ArrowRight size={17} /></button>
      </header>
      <div className="tailor-request-kpis">
        <article><ClipboardList size={24} /><span><small>Total records</small><strong>{String(rows.length).padStart(2, "0")}</strong><em>{rows.length ? "All booking requests" : "No records yet"}</em></span></article>
        <article><AlertTriangle size={24} /><span><small>Needs attention</small><strong>{String(pending.length).padStart(2, "0")}</strong><em>Priority queue</em></span></article>
        <article><CheckCircle2 size={24} /><span><small>Completed</small><strong>{completionRate}%</strong><em>Requests responded to</em></span></article>
        <article><RefreshCw size={24} /><span><small>Last refreshed</small><strong>Now</strong><em>Live dashboard data</em></span></article>
      </div>
      {message ? <div className={message.includes("successfully") || message.includes("rejected") ? "notice ok" : "error"} role="status">{message}</div> : null}
      <section className="tailor-record-panel" id="tailor-request-records">
        <div className="tailor-record-toolbar">
          <label><Search size={20} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search current records" /></label>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter booking requests by status">
            <option value="ALL">All statuses</option>
            <option value="PENDING">Pending</option>
            <option value="ACCEPTED">Accepted</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="REJECTED">Rejected</option>
            <option value="CLOSED">Closed</option>
          </select>
          <button type="button" className="secondary-btn" onClick={exportRequests} disabled={!filteredRows.length}>Export</button>
        </div>
        {filteredRows.length ? (
          <div className="tailor-record-table-wrap">
            <table className="tailor-record-table">
              <thead><tr><th>Request</th><th>Customer</th><th>Service</th><th>Preferred slot</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody>{filteredRows.map((row) => (
                <tr key={row.id}>
                  <td><strong>{row.requirement_code || row.id}</strong></td>
                  <td><strong>{row.customer_name || "Customer"}</strong><small>{row.customer_area || "Area not provided"}</small></td>
                  <td>{row.tailor_service_name || row.service_name || "Tailoring service"}<small>{row.quantity ? `Quantity ${row.quantity}` : row.measurement_mode}</small></td>
                  <td>{fmtDay(row.preferred_date)}<small>{row.preferred_time_slot || row.time_slot || row.measurement_mode || "Slot to be confirmed"}</small></td>
                  <td><StatusPill value={row.status} /></td>
                  <td>{String(row.status || "").toUpperCase() === "PENDING" ? <div className="inline-actions tailor-request-actions"><button type="button" className="primary-btn" onClick={() => accept(row)} disabled={workingId === row.id}>{workingId === row.id ? "Working..." : "Accept"}</button><button type="button" className="danger-link" onClick={() => reject(row)} disabled={workingId === row.id}>Reject</button></div> : <span className="tailor-responded-at">{fmtDate(row.responded_at || row.ts)}</span>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <Empty text="No booking requests match these filters." />}
        <footer className="tailor-record-footer">Showing {filteredRows.length} of {rows.length} records</footer>
      </section>
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

  async function reject(row) {
    if (!window.confirm("Reject this waiting-list booking?")) return;
    const reason = window.prompt("Reason for rejecting this request:", "Unable to accept this booking") || "Unable to accept this booking";
    setBusy(row.id);
    try {
      const res = await api.tailorRejectBooking(row.id, reason);
      setMessage(res.message || "Booking request rejected.");
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
                {String(row.status || "").toUpperCase() === "PENDING_APPROVAL" ? <ExpiryCountdown expiresAt={row.expiresAt || row.expires_at} /> : null}
                {row.customerLocationAddress || row.customer_location_address ? <small>{row.customerLocationAddress || row.customer_location_address}</small> : null}
              </div>
              <div>
                <span className="waiting-pill"><span className="live-dot" /> Waiting</span>
                <div className="inline-actions"><button type="button" className="primary-btn compact-action" onClick={() => confirm(row)} disabled={busy === row.id}>{busy === row.id ? "Working..." : "Accept"}</button><button type="button" className="danger-link" onClick={() => reject(row)} disabled={busy === row.id}>Reject</button></div>
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
            <PaginatedCards
              items={activeRows}
              pageSize={6}
              className="tailor-order-list"
              label="orders"
              renderItem={(order) => (
                <TailorOrderCard
                  order={order}
                  reload={reload}
                  onCharge={() => addCharge(order)}
                  onMeasurementDone={() => markMeasurementDone(order)}
                />
              )}
            />
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

  const [visitOpen, setVisitOpen] = useState(false);
  const [measurementReady, setMeasurementReady] = useState(!isTailorVisitOrder(order) || isMeasurementArrivalVerified(order));
  const paid = String(order.payment_status || order.paymentStatus || "").toLowerCase() === "paid";
  const completed = isCompletedOrder(order);
  const tailorVisit = isTailorVisitOrder(order);

  useEffect(() => {
    setStage(order.tracker_stage || order.trackerStage || "Order Placed");
    setMeasurementReady(!isTailorVisitOrder(order) || isMeasurementArrivalVerified(order));
    setVisitOpen(false);
  }, [order.tracker_stage, order.trackerStage, order.id, order.measurementMode, order.measurement_mode, order.measurementOtpVerifiedAt, order.measurement_otp_verified_at]);
  const stageOptions = bookingTrackerStages.filter((value) => value !== "Delivered");
  const statusValue = String(order.status || "").toLowerCase();
  const canMarkMeasurementDone = ["auto_approved", "measurement_pending", "tailor_confirmed"].includes(statusValue);

  async function acceptWaitlistedBooking() {
    setBusy(true);
    setMessage("");
    try {
      const res = await api.tailorConfirmBooking(order.id);
      setMessage(res.message || "Booking confirmed.");
      await reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

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

  if (["waitlisted", "waiting_list", "pending_approval"].includes(statusValue)) {
    return (
      <div className="order-actions tracker-actions waiting-order-actions">
        <small>This booking is waiting for your approval.</small>
        <button type="button" className="primary-btn" onClick={acceptWaitlistedBooking} disabled={busy}>
          {busy ? "Approving..." : "Accept Waitlisted Booking"}
        </button>
        {message ? <small className={message.toLowerCase().includes("confirmed") ? "field-success" : "field-error"}>{message}</small> : null}
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
      {!completed && canMarkMeasurementDone ? <button onClick={onMeasurementDone} disabled={busy || !measurementReady}>Measurement Done</button> : null}
      <button onClick={onCharge} disabled={busy}>Charge</button>
      <button type="button" className={visitOpen ? "active" : ""} onClick={() => setVisitOpen((open) => !open)} disabled={busy}>
        {tailorVisit ? "Visit tracking" : "Visit details"}
      </button>
      <div className={paid ? "delivery-otp-box unlocked" : "delivery-otp-box locked"}>
        <small>{paid ? "Delivery OTP enabled." : "Complete payment to enable delivery OTP."}</small>
        <button type="button" onClick={sendOtp} disabled={!paid || busy}>Send OTP</button>
        <input value={otp} onChange={(e) => setOtp(cleanDigits(e.target.value))} inputMode="numeric" maxLength={6} placeholder="Handover OTP" disabled={!paid || busy} />
        <button type="button" onClick={verifyOtp} disabled={!paid || busy || !otp}>Verify OTP</button>
      </div>
      {visitOpen ? <TailorMeasurementVisitPanel order={order} reload={reload} onReadyChange={setMeasurementReady} /> : null}
      {canMarkMeasurementDone && !measurementReady ? <small className="field-error">Verify the customer's arrival OTP before marking measurement done.</small> : null}
      {message ? <small className={message.includes("sent") || message.includes("verified") || message.includes("updated") || message.includes("unlocked") || message.includes("shared") || message.includes("marked") ? "field-success" : "field-error"}>{message}</small> : null}
    </div>
  );
}

function TailorOrderCard({ order, reload, onCharge, onMeasurementDone }) {
  const [open, setOpen] = useState(false);
  const stage = order.tracker_stage || order.trackerStage || "Order Placed";
  const stageIndex = Math.max(0, bookingTrackerStages.indexOf(stage));
  const progress = Math.round(((stageIndex + 1) / bookingTrackerStages.length) * 100);
  const phone = order.customer_phone || order.customerPhone || "";

  return (
    <article className={`tailor-order-card ${open ? "expanded" : ""}`}>
      <div className="tailor-order-summary">
        <div className="tailor-order-identity">
          <strong>{order.code}</strong>
          <h4>{order.service_name || order.serviceName || "Tailoring service"}</h4>
          <span>{order.customer_name || order.customerName || "Customer"}{phone ? ` · ${phone}` : ""}</span>
        </div>
        <div className="tailor-order-state">
          <StatusPill value={order.status} />
          <StatusPill value={order.payment_status || order.paymentStatus} />
        </div>
        <div className="tailor-order-facts">
          <span><small>Due</small><b>{fmtDay(order.expected_completion || order.expectedCompletion)}</b></span>
          <span><small>Total</small><b>{money(order.total)}</b></span>
        </div>
        <button
          type="button"
          className="tailor-order-expand"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
        >
          <span>{open ? "Hide controls" : "Manage order"}</span>
          <ChevronDown size={17} />
        </button>
      </div>
      <div className="tailor-order-progress" aria-label={`${stage}, ${progress}% complete`}>
        <span><i style={{ width: `${progress}%` }} /></span>
        <b>{stage}</b>
      </div>
      {open ? (
        <div className="tailor-order-expanded">
          <TailorOrderActions order={order} reload={reload} onCharge={onCharge} onMeasurementDone={onMeasurementDone} />
        </div>
      ) : null}
    </article>
  );
}

function AdminApp({ onLogout }) {
  const { language, setLanguage, t } = useLanguage();
  const [section, setSection] = useAppHistoryState("adminSection", "dashboard");
  const [data, setData] = useState({ metrics: {}, customers: [], tailors: [], requests: [], orders: [], payments: [], paymentIntents: [], withdrawalRequests: [], reviews: [], supportTickets: [], complaints: [], audit: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  async function loadAll(silent = false) {
    if (!silent) setLoading(true);
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
      if (!silent) setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);
  useAutoRefresh(() => loadAll(true));

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
            <button className="danger-btn" onClick={async () => {
              if (!window.confirm("Reject this tailor application?")) return;
              await api.rejectTailor(r.id, prompt("Reject reason:") || "Documents incomplete");
              reload();
            }}>Reject</button>
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
