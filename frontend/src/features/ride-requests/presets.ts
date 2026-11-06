/**
 * Popular Mumbai landmark coordinate presets for easy testing and rapid selection.
 * Coordinates are WGS 84 (Latitude, Longitude).
 */

export interface LocationPreset {
  name: string;
  latitude: number;
  longitude: number;
}

export const MUMBAI_LOCATION_PRESETS: LocationPreset[] = [
  {
    name: 'Bandra Kurla Complex (BKC)',
    latitude: 19.0657,
    longitude: 72.8687,
  },
  {
    name: 'Mumbai Airport (T2 CSMIA)',
    latitude: 19.0886,
    longitude: 72.8679,
  },
  {
    name: 'CSMT / Colaba (South Mumbai)',
    latitude: 18.9402,
    longitude: 72.8356,
  },
  {
    name: 'Powai (IIT Bombay / Hiranandani)',
    latitude: 19.1176,
    longitude: 72.906,
  },
  {
    name: 'Lower Parel (One World Center)',
    latitude: 19.0016,
    longitude: 72.8311,
  },
  {
    name: 'Dadar Station (Central Hub)',
    latitude: 19.0178,
    longitude: 72.8478,
  },
  {
    name: 'Andheri West (Infiniti Mall)',
    latitude: 19.1412,
    longitude: 72.8315,
  },
];
