# Goblin Mercenary Company

## What this app is

Goblin Mercenary Company is a standalone browser game in this repository. You lead the Brass Button Mercenary Company as its Captain. Complete all three contracts and bring the company home.

The start screen states the goal. A short onboarding explains contracts, preparation, encounters, and recovery.

The company tracks gold, rations, reputation, crew health, and completed contracts. Its roster includes Nix, the lieutenant and reserve quartermaster; Mog, the frontline fighter; Mara, the healer; and Grit, the bomber.

Choose a contract, then select two crew members and buy rations during preparation. You can return to the contract board before launching without losing supplies you bought. In each deterministic encounter, choose a strike, heal, or bomb action. Enemy threats follow a fixed order. These choices affect crew health and the chance to win.

Claim rewards after a victory. The crew recovers two health between successful contracts. Defeat ends the run and keeps crew injuries. Complete all three contracts to win the campaign.

The browser saves the current run in local storage. Reload the page to resume. Select **Reset company** to clear the saved run and start a new company.

The game requires no account, credentials, network connection, or external service.

## Run, build, test, and typecheck

From the repository root, install workspace dependencies with `pnpm install`.

Run the following commands from the repository root.

Start the local development server:

```sh
pnpm -F @proj-airi/goblin-mercenary dev
```

Open the local URL that Vite prints in your browser.

Build the app:

```sh
pnpm -F @proj-airi/goblin-mercenary build
```

Run the app's tests:

```sh
pnpm -F @proj-airi/goblin-mercenary test
```

Run the app's typecheck:

```sh
pnpm -F @proj-airi/goblin-mercenary typecheck
```

## When to use this app

Use this app to play or develop the standalone company campaign. It covers the contract board, crew preparation, deterministic encounters, rewards, injuries, and recovery.

## When not to use this app

Do not use this app for AIRI chat, speech, Live2D, provider calls, or other AIRI integrations. AIRI integration is deferred until the standalone game acceptance bar passes.
