import { test, expect } from "@playwright/test";
import path from "node:path";

test("upload scan, inspect evidence, review a field, ask and follow a citation", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.locator(".reference-badge")).toHaveText(
    "RECORDED FIXTURE DEMO",
  );
  await expect(
    page.getByRole("heading", { name: "Every document. Every detail." }),
  ).toBeVisible();
  const file = path.resolve("../fixtures/documents/synthetic-invoice.pdf");
  await page
    .getByLabel("Upload files")
    .setInputFiles([
      file,
      path.resolve("../fixtures/documents/synthetic-contract.pdf"),
    ]);
  const contract = page
    .getByRole("row")
    .filter({ hasText: "synthetic-contract.pdf" });
  await expect(contract).toContainText(/Ready|Needs review/, {
    timeout: 60_000,
  });
  const row = page
    .getByRole("row")
    .filter({ hasText: "synthetic-invoice.pdf" });
  await expect(row).toContainText(/Ready|Needs review/, { timeout: 540_000 });
  await row
    .getByRole("button", { name: /synthetic-invoice.pdf/ })
    .first()
    .click();
  await page.getByRole("button", { name: /Total amount/ }).click();
  await expect(page.locator(".highlight").first()).toBeVisible();
  await expect(
    page.getByAltText("Source page 1 of synthetic-invoice.pdf"),
  ).toBeVisible();
  await page.getByLabel("Edit Total amount").fill("2400.00");
  await page.getByRole("button", { name: "Verify field" }).click();
  await expect(
    page.getByText("Human verified", { exact: false }),
  ).toBeVisible();
  await page
    .getByLabel("What would you like to know?")
    .fill("What is the total due on the invoice?");
  await page.getByRole("button", { name: "Find evidence" }).click();
  await expect(page.locator(".citation").first()).toContainText("2400.00", {
    timeout: 120_000,
  });
  await page.locator(".citation button").first().click();
  await expect(page.getByText("Page 1 of 1")).toBeVisible();
  await page.getByRole("button", { name: /Total amount/ }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: process.env.SCREENSHOT_PATH || "test-results/workspace.png",
    fullPage: true,
  });
  if (process.env.COVER_PATH) {
    await page.screenshot({ path: process.env.COVER_PATH, fullPage: false });
  }
  await page.getByLabel("Upload files").setInputFiles(file);
  await expect(page.getByRole("status")).toContainText("duplicate");
  await expect(row).toHaveCount(1);
  await page
    .getByLabel("What would you like to know?")
    .fill("What is the penguin population in Antarctica?");
  await page.getByRole("button", { name: "Find evidence" }).click();
  await expect(
    page.getByText("I could not find supporting evidence", { exact: false }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Upload documents" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
