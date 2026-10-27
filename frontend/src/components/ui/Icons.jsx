// One small, consistent icon vocabulary for the support interface.
// These SVGs use currentColor, so the theme and button states control appearance.
const paths = {
  chat: "M5 4.5h14a1.5 1.5 0 0 1 1.5 1.5v10a1.5 1.5 0 0 1-1.5 1.5H9l-5.5 3V6A1.5 1.5 0 0 1 5 4.5Z",
  book: "M4 5.5h6l2 1.5 2-1.5h6v14h-6l-2 1-2-1H4Z M12 7v13",
  edit: "M13 5H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8 M10 15l1-4L19 3l3 3-8 8-4 1Z",
  search: "M16 16l5 5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z",
  panel:
    "M5 3.5h14a1.5 1.5 0 0 1 1.5 1.5v14a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 1-1.5-1.5V5A1.5 1.5 0 0 1 5 3.5Z M9 4v16",
  menu: "M4 6h16 M4 12h16 M4 18h16",
  close: "m6 6 12 12 M18 6 6 18",
  plus: "M12 4v16 M4 12h16",
  up: "M12 20V4 M5 11l7-7 7 7",
  right: "M4 12h16 M13 5l7 7-7 7",
  chevron: "m8 4 8 8-8 8",
  down: "m5 9 7 7 7-7",
  check: "m4 12 5 5L20 6",
  square:
    "M6 5h12a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z",
  copy: "M8 8h12v13H8Z M16 8V3H3v13h5",
  refresh: "M4 9a8 8 0 1 1 0 6 M4 3v6h6",
  alert: "M12 8v5 M12 17h.01 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z",
  help: "M9 8a3 3 0 0 1 6 0c0 3-3 2-3 5 M12 17h.01 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z",
  shield: "m12 2 8 3v6c0 5-4 8-8 11-4-3-8-6-8-11V5l8-3Z m-4 10 3 3 5-6",
  file: "M14 2H5v20h14V7l-5-5Z M14 2v6h5 M8 12h8 M8 16h6",
  external: "M14 3h7v7 M21 3 10 14 M10 4H4v16h16v-6",
  trash: "M3 6h18 M9 6V3h6v3 M6 6l1 15h10l1-15 M10 10v7 M14 10v7",
  settings: "M3 7h18 M3 17h18 M8 4v6 M16 14v6",
};

function icon(name) {
  return function Icon({ size = 18, strokeWidth = 1.5, ...props }) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        {...props}
      >
        <path d={paths[name]} />
      </svg>
    );
  };
}

export const MessageSquare = icon("chat");
export const BookOpen = icon("book");
export const Compose = icon("edit");
export const Search = icon("search");
export const PanelRight = icon("panel");
export const Menu = icon("menu");
export const X = icon("close");
export const Plus = icon("plus");
export const ArrowUp = icon("up");
export const ArrowRight = icon("right");
export const ChevronRight = icon("chevron");
export const ChevronDown = icon("down");
export const Check = icon("check");
export const Square = icon("square");
export const Copy = icon("copy");
export const RotateCcw = icon("refresh");
export const RefreshCw = icon("refresh");
export const AlertCircle = icon("alert");
export const CircleHelp = icon("help");
export const ShieldCheck = icon("shield");
export const FileText = icon("file");
export const FileCheck2 = icon("file");
export const ExternalLink = icon("external");
export const Trash2 = icon("trash");
export const Settings2 = icon("settings");
