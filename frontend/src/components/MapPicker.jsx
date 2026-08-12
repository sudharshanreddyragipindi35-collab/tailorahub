import React, { useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_CENTER = { latitude: 13.0827, longitude: 80.2707 };
let googleMapsPromise;

function mapsConfig() {
  return {
    provider: (import.meta.env.VITE_MAPS_PROVIDER || "mock").toLowerCase(),
    apiKey: import.meta.env.VITE_MAPS_API_KEY || "",
  };
}

function loadGoogleMaps(apiKey) {
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (!googleMapsPromise) {
    googleMapsPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve(window.google.maps);
      script.onerror = () => reject(new Error("Google Maps could not be loaded"));
      document.head.appendChild(script);
    });
  }
  return googleMapsPromise;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function readableAddress(input, point) {
  return input?.trim() || `Pinned location near ${point.latitude.toFixed(5)}, ${point.longitude.toFixed(5)}`;
}

function pointFromCanvas(event, container) {
  const rect = container.getBoundingClientRect();
  const x = clamp((event.clientX - rect.left) / rect.width, 0, 1);
  const y = clamp((event.clientY - rect.top) / rect.height, 0, 1);
  return {
    latitude: Number((DEFAULT_CENTER.latitude + (0.5 - y) * 0.12).toFixed(7)),
    longitude: Number((DEFAULT_CENTER.longitude + (x - 0.5) * 0.12).toFixed(7)),
  };
}

function pinStyle(point) {
  const x = clamp(((point.longitude - DEFAULT_CENTER.longitude) / 0.12) + 0.5, 0.08, 0.92);
  const y = clamp(0.5 - ((point.latitude - DEFAULT_CENTER.latitude) / 0.12), 0.08, 0.92);
  return { left: `${x * 100}%`, top: `${y * 100}%` };
}

function MockMapPicker({ query, setQuery, point, setPoint, setAddress }) {
  const mapRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function movePin(event) {
    if (!mapRef.current) return;
    const nextPoint = pointFromCanvas(event, mapRef.current);
    setPoint(nextPoint);
    setAddress(readableAddress(query, nextPoint));
  }

  useEffect(() => {
    if (!dragging) return undefined;
    function onMove(event) {
      movePin(event);
    }
    function onUp() {
      setDragging(false);
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp, { once: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [dragging, query]);

  function useTypedAddress() {
    const seed = [...query].reduce((sum, char) => sum + char.charCodeAt(0), 0);
    const nextPoint = {
      latitude: Number((DEFAULT_CENTER.latitude + ((seed % 70) - 35) / 10000).toFixed(7)),
      longitude: Number((DEFAULT_CENTER.longitude + (((seed * 3) % 70) - 35) / 10000).toFixed(7)),
    };
    setPoint(nextPoint);
    setAddress(readableAddress(query, nextPoint));
  }

  return (
    <>
      <div className="map-search-row">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search shop address or landmark" />
        <button type="button" className="secondary-btn" onClick={useTypedAddress}>Search</button>
      </div>
      <div className="map-surface mock-map" ref={mapRef} onPointerDown={movePin}>
        <div className="map-grid-lines" />
        <div className="map-road primary" />
        <div className="map-road secondary" />
        <div className="map-zone-label">Move pin to exact shop entrance</div>
        <button
          type="button"
          className={dragging ? "map-pin dragging" : "map-pin"}
          style={pinStyle(point)}
          onPointerDown={(event) => {
            event.stopPropagation();
            setDragging(true);
          }}
          aria-label="Drag location pin"
        >
          <span />
        </button>
      </div>
    </>
  );
}

function GoogleMapPicker({ initialLocation, query, setQuery, point, setPoint, setAddress, setMessage }) {
  const mapRef = useRef(null);
  const inputRef = useRef(null);
  const markerRef = useRef(null);
  const geocoderRef = useRef(null);

  useEffect(() => {
    const { apiKey } = mapsConfig();
    let cancelled = false;
    if (!apiKey) return undefined;
    loadGoogleMaps(apiKey)
      .then((maps) => {
        if (cancelled || !mapRef.current) return;
        const center = { lat: point.latitude, lng: point.longitude };
        const map = new maps.Map(mapRef.current, {
          center,
          zoom: 16,
          disableDefaultUI: true,
          zoomControl: true,
          clickableIcons: false,
        });
        const marker = new maps.Marker({
          map,
          position: center,
          draggable: true,
          animation: maps.Animation.DROP,
        });
        markerRef.current = marker;
        geocoderRef.current = new maps.Geocoder();

        if (inputRef.current && maps.places) {
          const autocomplete = new maps.places.Autocomplete(inputRef.current, {
            fields: ["formatted_address", "geometry", "name"],
          });
          autocomplete.addListener("place_changed", () => {
            const place = autocomplete.getPlace();
            const location = place.geometry?.location;
            if (!location) return;
            const nextPoint = { latitude: location.lat(), longitude: location.lng() };
            setPoint(nextPoint);
            setAddress(place.formatted_address || place.name || readableAddress(query, nextPoint));
            marker.setPosition({ lat: nextPoint.latitude, lng: nextPoint.longitude });
            map.panTo({ lat: nextPoint.latitude, lng: nextPoint.longitude });
          });
        }

        marker.addListener("dragend", () => {
          const position = marker.getPosition();
          const nextPoint = { latitude: position.lat(), longitude: position.lng() };
          setPoint(nextPoint);
          geocoderRef.current.geocode({ location: { lat: nextPoint.latitude, lng: nextPoint.longitude } }, (results, status) => {
            if (status === "OK" && results?.[0]) setAddress(results[0].formatted_address);
            else setAddress(readableAddress(query, nextPoint));
          });
        });
      })
      .catch((error) => setMessage(error.message));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!markerRef.current) return;
    markerRef.current.setPosition({ lat: point.latitude, lng: point.longitude });
  }, [point.latitude, point.longitude]);

  return (
    <>
      <div className="map-search-row">
        <input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search shop address or landmark" />
      </div>
      <div className="map-surface google-map" ref={mapRef} aria-label="Location map">
        {initialLocation ? null : <div className="loading">Loading map...</div>}
      </div>
    </>
  );
}

export default function MapPicker({ initialLocation, onConfirm, confirmLabel = "Confirm this location" }) {
  const config = useMemo(mapsConfig, []);
  const [query, setQuery] = useState(initialLocation?.address_text || initialLocation?.addressText || "");
  const [address, setAddress] = useState(initialLocation?.address_text || initialLocation?.addressText || "");
  const [point, setPoint] = useState({
    latitude: Number(initialLocation?.latitude || DEFAULT_CENTER.latitude),
    longitude: Number(initialLocation?.longitude || DEFAULT_CENTER.longitude),
  });
  const [message, setMessage] = useState(config.provider === "google" && !config.apiKey ? "Google Maps key is not configured, using mock map picker." : "");

  const location = useMemo(() => ({
    address_text: readableAddress(address || query, point),
    latitude: Number(point.latitude),
    longitude: Number(point.longitude),
  }), [address, query, point.latitude, point.longitude]);

  function confirm() {
    onConfirm?.(location);
  }

  const useGoogle = config.provider === "google" && config.apiKey;

  return (
    <div className="map-picker">
      {useGoogle ? (
        <GoogleMapPicker
          initialLocation={initialLocation}
          query={query}
          setQuery={setQuery}
          point={point}
          setPoint={setPoint}
          setAddress={setAddress}
          setMessage={setMessage}
        />
      ) : (
        <MockMapPicker query={query} setQuery={setQuery} point={point} setPoint={setPoint} setAddress={setAddress} />
      )}
      {message ? <div className="notice">{message}</div> : null}
      <div className="map-confirm-panel">
        <div>
          <strong>{location.address_text}</strong>
          <small>{location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}</small>
        </div>
        <button type="button" className="ok-btn" onClick={confirm}>{confirmLabel}</button>
      </div>
    </div>
  );
}
