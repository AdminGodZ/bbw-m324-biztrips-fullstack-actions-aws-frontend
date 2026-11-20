import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Employees from "./Employees";

afterEach(() => vi.unstubAllGlobals());

const employees = [
  {id: 1, name: "Joe Sarnataro", jobTitle: "SW-Engineer", profilePictureFilename: "0b6f0b1e-7d2a-4c55-9a51-6d3b4f6f1a2b.png"},
  {id: 2, name: "Sam Sony", jobTitle: "Web-Architect", profilePictureFilename: null},
];

test("shows stored photos from the backend and a placeholder otherwise", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok: true, json: async () => employees}));
  render(<Employees/>);
  const photo = await screen.findByAltText("Foto von Joe Sarnataro");
  expect(photo.getAttribute("src")).toMatch(/^\/v1\/employees\/1\/photo\?v=/);
  expect(screen.getByLabelText("Kein Foto von Sam Sony")).toBeInTheDocument();
});

test("uploads a photo as multipart form data and displays it", async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce({ok: true, json: async () => employees})
    .mockResolvedValueOnce({ok: true});
  vi.stubGlobal("fetch", fetch);
  const user = userEvent.setup();
  render(<Employees/>);
  await screen.findByText("Sam Sony");
  const file = new File([new Uint8Array([137, 80, 78, 71])], "sam.png", {type: "image/png"});
  await user.upload(document.getElementById("photo-2"), file);
  const [url, options] = fetch.mock.calls[1];
  expect(url).toBe("/v1/employees/2/photo");
  expect(options.method).toBe("POST");
  expect(options.body.get("file").name).toBe("sam.png");
  expect(await screen.findByAltText("Foto von Sam Sony")).toBeInTheDocument();
});

test("shows the backend error message when S3 is unavailable", async () => {
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce({ok: true, json: async () => employees})
    .mockResolvedValueOnce({ok: false, status: 503, json: async () => ({detail: "Der Bilder-Speicher ist momentan nicht verfügbar."})}));
  const user = userEvent.setup();
  render(<Employees/>);
  await screen.findByText("Sam Sony");
  await user.upload(document.getElementById("photo-2"), new File(["x"], "x.png", {type: "image/png"}));
  expect(await screen.findByRole("status")).toHaveTextContent("Bilder-Speicher ist momentan nicht verfügbar");
});
