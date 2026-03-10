import { describe, expect, it } from "vitest";

import { router } from "./router";


describe("frontend routes", () => {
  it("includes chat/settings/analytics paths", () => {
    expect(router.routesByPath["/chat"]).toBeDefined();
    expect(router.routesByPath["/settings"]).toBeDefined();
    expect(router.routesByPath["/analytics"]).toBeDefined();
  });
});
