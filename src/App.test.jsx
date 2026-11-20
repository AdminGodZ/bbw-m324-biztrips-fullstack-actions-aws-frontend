import {render, screen} from "@testing-library/react";
import App from "./App";
import {WishlistProvider} from "./components/wishlistContext.jsx";
import userEvent from '@testing-library/user-event';

beforeEach(() => {
  globalThis.fetch = vi.fn(() =>
    Promise.resolve({ok: true, json: () => Promise.resolve([])})
  );
});

test("renders without crashing", () => {
  render(
    <WishlistProvider>
      <App/>
    </WishlistProvider>
  );
  expect(screen.getByText(/RefCard 05 - Business Trips - Full Stack on AWS/i)).toBeInTheDocument();
});

test("adds a fetched trip to the wishlist and removes it", async () => {
  const user = userEvent.setup();
  globalThis.fetch.mockResolvedValue({ok: true, json: async () => [
    {id: 1, title: 'BT01', description: 'Conference', startTrip: '2026-02-13T00:00:00', endTrip: '2026-02-15T16:56:00'}
  ]});
  render(<WishlistProvider><App/></WishlistProvider>);
  await user.click(await screen.findByRole('button', {name: /add to wishlist/i}));
  expect(screen.getByRole('button', {name: /added to wishlist/i})).toBeDisabled();
  expect(JSON.parse(localStorage.getItem('wishlist'))).toHaveLength(1);
  await user.click(screen.getByRole('button', {name: /remove/i}));
  expect(screen.getByRole('button', {name: /add to wishlist/i})).toBeEnabled();
  expect(JSON.parse(localStorage.getItem('wishlist'))).toHaveLength(0);
});
