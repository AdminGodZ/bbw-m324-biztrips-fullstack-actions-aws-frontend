import {getBusinessTrips} from './tripsService';

afterEach(() => vi.unstubAllGlobals());

test('loads trips from the same-origin API', async () => {
  const trips = [{id: 1, title: 'BT01'}];
  const fetch = vi.fn().mockResolvedValue({ok: true, json: async () => trips});
  vi.stubGlobal('fetch', fetch);
  await expect(getBusinessTrips()).resolves.toEqual(trips);
  expect(fetch).toHaveBeenCalledWith('/v1/trips');
});

test('propagates a backend failure', async () => {
  const response = {ok: false, status: 503};
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
  await expect(getBusinessTrips()).rejects.toBe(response);
});
