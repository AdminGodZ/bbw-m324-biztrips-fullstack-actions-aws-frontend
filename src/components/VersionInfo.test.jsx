import {render, screen} from "@testing-library/react";
import VersionInfo from "./VersionInfo";

afterEach(() => vi.unstubAllGlobals());

test("shows frontend build version and backend version from /actuator/info", async () => {
  const fetch = vi.fn().mockResolvedValue({ok: true, json: async () => ({app: {version: "5.0.0"}})});
  vi.stubGlobal("fetch", fetch);
  render(<VersionInfo/>);
  expect(await screen.findByText("5.0.0")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith("/actuator/info");
  expect(screen.getByTestId("versions")).toHaveTextContent("Frontend dev");
});

test("reports an unreachable backend", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network")));
  render(<VersionInfo/>);
  expect(await screen.findByText("nicht erreichbar")).toBeInTheDocument();
});
