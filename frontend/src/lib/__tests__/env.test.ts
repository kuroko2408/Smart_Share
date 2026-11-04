import { describe, it, expect } from 'vitest';
import { env } from '../env';

describe('env', () => {
  it('provides a default apiBaseUrl', () => {
    expect(env.apiBaseUrl).toBeTruthy();
  });

  it('provides a default mapTileUrl', () => {
    expect(env.mapTileUrl).toContain('openstreetmap');
  });
});
