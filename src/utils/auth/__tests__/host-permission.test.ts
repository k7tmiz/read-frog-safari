// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => {
  const contains = vi.fn<(...args: any[]) => Promise<boolean>>()
  const request = vi.fn<(...args: any[]) => Promise<boolean>>()
  return {
    contains,
    request,
    browser: {
      permissions: {
        contains: (...args: any[]) => contains(...args),
        request: (...args: any[]) => request(...args),
      },
    },
  }
})

vi.mock("#imports", () => ({ browser: mocks.browser }))
vi.mock("wxt/browser", () => ({ browser: mocks.browser }))
vi.mock("@/env", () => ({
  env: {
    WXT_API_URL: "https://api.readfrog.app",
    WXT_WEBSITE_URL: "https://www.readfrog.app",
  },
}))

import { hasAccountHostPermission, requestAccountHostPermission } from "../host-permission"

beforeEach(() => {
  vi.unstubAllEnvs()
  mocks.contains.mockReset()
  mocks.request.mockReset()
})

describe("account host permission", () => {
  it("treats Safari as granted without calling the permissions API", async () => {
    vi.stubEnv("BROWSER", "safari")

    await expect(hasAccountHostPermission()).resolves.toBe(true)
    await expect(requestAccountHostPermission()).resolves.toBe(true)
    expect(mocks.contains).not.toHaveBeenCalled()
    expect(mocks.request).not.toHaveBeenCalled()
  })

  it("reads and requests the permission on Chrome", async () => {
    vi.stubEnv("BROWSER", "chrome")
    mocks.contains.mockResolvedValue(false)
    mocks.request.mockResolvedValue(true)

    await expect(hasAccountHostPermission()).resolves.toBe(false)
    await expect(requestAccountHostPermission()).resolves.toBe(true)
    expect(mocks.contains).toHaveBeenCalledOnce()
    expect(mocks.request).toHaveBeenCalledOnce()
  })
})
