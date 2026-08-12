import React, { useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_CENTER = { latitude: 13.0827, longitude: 80.2707 };
let googleMapsPromise;

function isLocalGoogleReferrerMismatch() {
  const { hostname, origin } = window.location;
  const isLocal = hostname === "127.0.0.1" || hostname === "localhost";
  const allowedLocalOrigins = new Set(["http://127.0.0.1:5173", "http://localhost:5173"]);
  return isLocal && !allowedLocalOrigins.has(origin);
}

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

function pointFromLatLng(latLng) {
  return {
    latitude: Number(latLng.lat().toFixed(7)),
    longitude: Number(latLng.lng().toFixed(7)),
  };
}

function reverseGeocode(geocoder, point, fallback, setAddress, setMessage) {
  if (!geocoder) {
    setAddress(readableAddress(fallback, point));
    return;
  }
  geocoder.geocode({ location: { lat: point.latitude, lng: point.longitude } }, (results, status) => {
    if (status === "OK" && results?.[0]) {
      setAddress(results[0].formatted_address);
      return;
    }
    setAddress(readableAddress(fallback, point));
    if (status && status !== "ZERO_RESULTS") setMessage(`Address lookup failed: ${status}`);
  });
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

function MockMapPicker({ query, setQuery, point, setPoint, setAddress, setMessage }) {
  const mapRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [locating, setLocating] = useState(false);

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

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setMessage("Current location is not available in this browser.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const nextPoint = {
          latitude: Number(position.coords.latitude.toFixed(7)),
          longitude: Number(position.coords.longitude.toFixed(7)),
        };
        setPoint(nextPoint);
        setAddress(readableAddress("Current location", nextPoint));
        setMessage("");
        setLocating(false);
      },
      () => {
        setMessage("Location permission was not allowed. Search your address or move the pin manually.");
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 },
    );
  }

  return (
    <>
      <div className="map-search-row rapido-map-search">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search shop address or landmark" />
        <button type="button" className="secondary-btn" onClick={useTypedAddress}>Search</button>
      </div>
      <div className="map-stage">
        <div className="map-surface mock-map" ref={mapRef} onPointerDown={movePin}>
          <div className="map-grid-lines" />
          <div className="map-road primary" />
          <div className="map-road secondary" />
          <div className="map-zone-label">Drag or tap to place the pin exactly</div>
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
        <button type="button" className="map-location-btn" onClick={useCurrentLocation} disabled={locating}>
          {locating ? "Locating..." : "Use current location"}
        </button>
      </div>
    </>
  );
}

function GoogleMapPicker({ initialLocation, query, setQuery, point, setPoint, setAddress, setMessage }) {
  const mapRef = useRef(null);
  const inputRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const geocoderRef = useRef(null);
  const idleListenerRef = useRef(null);
  const autocompleteListenerRef = useRef(null);
  const idleTimerRef = useRef(null);
  const queryRef = useRef(query);
  const [locating, setLocating] = useState(false);

  useEffect(() => {
    queryRef.current = query;
  }, [query]);

  function moveToPoint(nextPoint, nextAddress) {
    setPoint(nextPoint);
    if (nextAddress) setAddress(nextAddress);
    if (mapInstanceRef.current) {
      mapInstanceRef.current.panTo({ lat: nextPoint.latitude, lng: nextPoint.longitude });
      mapInstanceRef.current.setZoom(Math.max(mapInstanceRef.current.getZoom() || 17, 17));
    }
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setMessage("Current location is not available in this browser.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const nextPoint = {
          latitude: Number(position.coords.latitude.toFixed(7)),
          longitude: Number(position.coords.longitude.toFixed(7)),
        };
        moveToPoint(nextPoint);
        reverseGeocode(geocoderRef.current, nextPoint, "Current location", setAddress, setMessage);
        setMessage("");
        setLocating(false);
      },
      () => {
        setMessage("Location permission was not allowed. Search your address or move the map manually.");
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 },
    );
  }

  useEffect(() => {
    const { apiKey } = mapsConfig();
    let cancelled = false;
    if (!apiKey) return undefined;
    const previousAuthFailure = window.gm_authFailure;
    window.gm_authFailure = () => {
      setMessage(
        isLocalGoogleReferrerMismatch()
          ? `Google Maps blocked this local URL. Open http://127.0.0.1:5173 or add ${window.location.origin}/* to the API key website restrictions.`
          : "Google Maps rejected the API key. Check billing, enabled APIs, and website restrictions in Google Cloud.",
      );
      previousAuthFailure?.();
    };
    if (isLocalGoogleReferrerMismatch()) {
      setMessage(`Google Maps key is restricted for port 5173, but this page is ${window.location.origin}. Use http://127.0.0.1:5173.`);
    }
    loadGoogleMaps(apiKey)
      .then((maps) => {
        if (cancelled || !mapRef.current) return;
        const center = { lat: point.latitude, lng: point.longitude };
        const map = new maps.Map(mapRef.current, {
          center,
          zoom: 17,
          disableDefaultUI: true,
          zoomControl: true,
          clickableIcons: false,
          fullscreenControl: false,
          gestureHandling: "greedy",
          mapTypeControl: false,
          streetViewControl: false,
        });
        mapInstanceRef.current = map;
        geocoderRef.current = new maps.Geocoder();

        if (inputRef.current && maps.places) {
          const autocomplete = new maps.places.Autocomplete(inputRef.current, {
            componentRestrictions: { country: "in" },
            fields: ["formatted_address", "geometry", "name"],
          });
          autocompleteListenerRef.current = autocomplete.addListener("place_changed", () => {
            const place = autocomplete.getPlace();
            const location = place.geometry?.location;
            if (!location) return;
            const nextPoint = pointFromLatLng(location);
            const nextAddress = place.formatted_address || place.name || readableAddress(queryRef.current, nextPoint);
            setQuery(nextAddress);
            moveToPoint(nextPoint, nextAddress);
            setMessage("");
          });
        }

        idleListenerRef.current = map.addListener("idle", () => {
          const centerPosition = map.getCenter();
          if (!centerPosition) return;
          const nextPoint = pointFromLatLng(centerPosition);
          setPoint(nextPoint);
          if (idleTimerRef.current) window.clearTimeout(idleTimerRef.current);
          idleTimerRef.current = window.setTimeout(() => {
            reverseGeocode(geocoderRef.current, nextPoint, queryRef.current, setAddress, setMessage);
          }, 250);
        });
      })
      .catch((error) => setMessage(error.message));
    return () => {
      cancelled = true;
      if (idleTimerRef.current) window.clearTimeout(idleTimerRef.current);
      idleListenerRef.current?.remove?.();
      autocompleteListenerRef.current?.remove?.();
      window.gm_authFailure = previousAuthFailure;
    };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const currentCenter = mapInstanceRef.current.getCenter();
    if (!currentCenter) return;
    const sameLat = Math.abs(currentCenter.lat() - point.latitude) < 0.000001;
    const sameLng = Math.abs(currentCenter.lng() - point.longitude) < 0.000001;
    if (!sameLat || !sameLng) mapInstanceRef.current.panTo({ lat: point.latitude, lng: point.longitude });
  }, [point.latitude, point.longitude]);

  return (
    <>
      <div className="map-search-row rapido-map-search">
        <input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search address, apartment, street or landmark" />
        <button type="button" className="secondary-btn" onClick={useCurrentLocation} disabled={locating}>
          {locating ? "Locating..." : "Current location"}
        </button>
      </div>
      <div className="map-stage">
        <div className="map-surface google-map" ref={mapRef} aria-label="Location map">
          {initialLocation ? null : <div className="loading">Loading real map...</div>}
        </div>
        <div className="map-help-chip">Move the map until the pin sits on the exact entrance</div>
        <div className="rapido-center-pin" aria-hidden="true">
          <span />
        </div>
        <div className="rapido-pin-shadow" aria-hidden="true" />
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
        <MockMapPicker query={query} setQuery={setQuery} point={point} setPoint={setPoint} setAddress={setAddress} setMessage={setMessage} />
      )}
      {message ? <div className="notice">{message}</div> : null}
      <div className="map-confirm-panel">
        <div>
          <span className="map-confirm-kicker">Selected location</span>
          <strong>{location.address_text}</strong>
          <small>{location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}</small>
        </div>
        <button type="button" className="ok-btn" onClick={confirm}>{confirmLabel}</button>
      </div>
    </div>
  );
}
