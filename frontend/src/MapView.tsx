import { useEffect, useMemo, useRef } from "react";
import Map, { Layer, Marker, Source, type MapRef } from "react-map-gl/maplibre";
import type { Hazard, Plan } from "./types";
import "maplibre-gl/dist/maplibre-gl.css";

const style = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export function MapView({ plan, selectedId, hour, hazard }: { plan: Plan; selectedId: string | null; hour: number; hazard: Hazard }) {
  const mapRef = useRef<MapRef>(null);
  const mounts = useRef(0);
  useEffect(() => {
    mounts.current += 1;
    (window as unknown as { __mapMounts?: number }).__mapMounts = mounts.current;
  }, []);

  const heat = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: plan.heatmap
        .map((point) => {
          const sample = point.hours[hour];
          if (!sample || sample[hazard] == null) return null;
          return {
            type: "Feature" as const,
            properties: { value: sample[hazard] },
            geometry: { type: "Point" as const, coordinates: [point.lng, point.lat] },
          };
        })
        .filter((feature) => feature !== null),
    }),
    [plan, hour, hazard],
  );

  useEffect(() => {
    const source = mapRef.current?.getSource("heat") as { setData?: (data: unknown) => void } | undefined;
    source?.setData?.(heat);
  }, [heat]);

  return (
    <Map
      ref={mapRef}
      initialViewState={{ longitude: -95, latitude: 37, zoom: 4 }}
      mapStyle={style}
      style={{ width: "100%", height: 520 }}
    >
      <Source id="heat" type="geojson" data={heat}>
        <Layer id="heat-layer" type="heatmap" paint={{ "heatmap-weight": ["interpolate", ["linear"], ["get", "value"], 0, 0, 55, 1], "heatmap-radius": 28 }} />
      </Source>
      {plan.routes.map((route) => (
        <Source key={route.id} id={route.id} type="geojson" data={{ type: "Feature", properties: {}, geometry: route.geometry }}>
          <Layer
            id={`${route.id}-line`}
            type="line"
            paint={{
              "line-color": route.id === selectedId ? "#f4b942" : "#8d99a6",
              "line-width": route.id === selectedId ? 5 : 2,
            }}
          />
        </Source>
      ))}
      {plan.routes.find((route) => route.id === selectedId)?.checkpoints.map((stop) => (
        <Marker key={stop.eta + stop.distance_miles} longitude={stop.lng} latitude={stop.lat} anchor="center">
          <span className={`pin ${stop.risk?.replace(" ", "-") ?? "Unknown"}`} title={stop.risk ?? "Unknown"} />
        </Marker>
      ))}
    </Map>
  );
}
