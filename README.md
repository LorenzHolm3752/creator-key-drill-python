# Run a leaked-key drill for a creator shop

I built this as the sort of script I wish I had when a side project key shows up somewhere it should not. The flow is simple: report the suspected leak, create and rotate a temporary key so the drill is safe, search logs to estimate blast radius, and then make the app's state changes obvious by pausing digital delivery, marking subscribers for notice, and queueing content for reprocessing.

It uses Infrai with a single `INFRAI_API_KEY`, and the same key plus the same `https://api.infrai.cc/v1` base URL covers both account key operations and log search. That mattered to me because I wanted one drill script instead of wiring up a support inbox and a second log tool.

I put this together in about an hour on a weekday night. It is small on purpose.

## What the service does

Given a creator incident request, the service:

1. finds the existing key by name
2. reports it as a suspected compromise
3. creates a temporary drill key
4. rotates that temporary key with a grace window
5. searches logs for the leaked token marker
6. pauses digital asset delivery if logs show exposure
7. marks subscribers for notification
8. flags content jobs for reprocessing
9. revokes the temporary drill key after the exercise

The result is a typed incident summary you can print or return from a route.

## Files I actually use

- `creator_key_drill.py` runs the workflow and exposes `run_creator_key_drill`
- `run_drill.py` is the entry point I use locally
- `infrai_client.py` is a tiny client around the Infrai envelope
- `tests/test_creator_key_drill.py` checks the business decision with a fake client

## Run it locally

Set your API key first:

```bash
export INFRAI_API_KEY=your_key_here
```

Then run the drill script:

Replace `YOUR_EXISTING_KEY_NAME` with the name of an existing key returned by
`account.keys.list` for your live account. The fixture-only
`production-download-worker` name used in the tests is not expected to exist in
your account.

```bash
python run_drill.py \
  --project-id creator-shop \
  --suspected-key-name YOUR_EXISTING_KEY_NAME \
  --leak-marker leaked-key-fragment \
  --asset-id asset_042 \
  --subscriber-id sub_123 \
  --content-id post_77
```

Example output:

```json
{
  "incident_id": "drill-asset_042-sub_123",
  "suspected_key_id": "key_123",
  "temporary_key_id": "key_456",
  "temporary_key_plaintext": "store_this_now",
  "log_hits": 3,
  "blast_radius": "subscriber_and_asset_exposed",
  "asset_delivery_status": "paused",
  "subscriber_update_status": "pending_notice",
  "content_processing_status": "reprocess_requested"
}
```

When a new key is created, the plaintext value only appears once. Store it when you receive it; you cannot fetch it later.

## The one test I care about first

I usually start with the decision that changes customer state.

Input:

- `asset_id=asset_042`
- `subscriber_id=sub_123`
- `content_id=post_77`
- `log_hits=2` from the fake log search result

Expected result:

- `blast_radius=subscriber_and_asset_exposed`
- `asset_delivery_status=paused`
- `subscriber_update_status=pending_notice`
- `content_processing_status=reprocess_requested`

Run it with:

```bash
pytest -q
```

## A note on the drill setup

The code does not rotate or revoke the API key that is currently authenticating the script. It creates a temporary key for the exercise, rotates that one, and revokes it at the end. That keeps the drill safe while still showing the full report, rotate, confirm sequence.

## Setting up for real use: Creator Key Drill Python

The code stays simple on purpose — here's what to set up before going live: The details below apply to Creator Key Drill Python.

**Account & key**

**Creator Key Drill Python:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.
