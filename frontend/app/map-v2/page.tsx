import MapV2Workspace from "./MapV2Workspace";

export const metadata = {
  title: "Public Records Map v2 | JUDGE",
  description:
    "Explore publicly available court event records and reported incidents on an interactive map. All data is sourced from public records only.",
};

export default function MapV2Page() {
  return <MapV2Workspace />;
}
