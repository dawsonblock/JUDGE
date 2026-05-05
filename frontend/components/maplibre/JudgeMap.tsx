"use client";

/**
 * JudgeMap.tsx — initializes a MapLibre GL map, exports MapLibreContext so
 * child components (layers, controls) can consume the map instance via
 * useContext without prop drilling.
 */

import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { TILE_STYLE_URL, DEFAULT_BOUNDS } from "./constants";

export const MapLibreContext = createContext<maplibregl.Map | null>(null);

/** Hook to access the map instance within a JudgeMap tree. */
export function useJudgeMap(): maplibregl.Map | null {
  return useContext(MapLibreContext);
}

type Props = {
  children?: ReactNode;
  className?: string;
};

export default function JudgeMap({ children, className = "" }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const instance = new maplibregl.Map({
      container: containerRef.current,
      style: TILE_STYLE_URL,
      center: DEFAULT_BOUNDS.center,
      zoom: DEFAULT_BOUNDS.zoom,
      attributionControl: false, // We add our own in JudgeMapLegend
    });

    instance.once("load", () => {
      setMap(instance);
    });

    return () => {
      instance.remove();
      setMap(null);
    };
  }, []);

  return (
    <MapLibreContext.Provider value={map}>
      <div className={`relative w-full h-full ${className}`}>
        <div ref={containerRef} className="absolute inset-0" />
        {map && children}
      </div>
    </MapLibreContext.Provider>
  );
}
