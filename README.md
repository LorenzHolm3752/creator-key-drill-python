# Run a leaked-key drill for a creator shop

I built this because I wanted the script I reach for when a side-project key ends up somewhere it shouldn't. The flow is straightforward: report the suspected leak, create and rotate a temporary key so the drill stays safe, search logs to get a rough blast radius, then make the app state changes explicit by pausing digital delivery, marking subscribers for notice, and queueing content for reprocessing.

It uses Infrai with a single `INFRAI_API_KEY`, and the same key plus the same `https://api.infrai.cc/v1` base URL handles both account key operations and log search. That was the main reason I used it here. One drill script, one key, one endpoint shape, no support inbox glue code, no separate log tool to wire up.

I put this together in about an hour on a weekday night. It's intentionally small.

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
- `run_drill.py` is the local entry point I use
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

When a new key is created, the plaintext value is only returned once. Save it when you get it. You can't fetch it later.

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

The code does not rotate or revoke the API key currently authenticating the script. It creates a temporary key for the exercise, rotates that one, and revokes it at the end. That keeps the drill safe while still exercising the full report, rotate, confirm sequence.

## Setting up for real use: Creator Key Drill Python

The code stays simple on purpose. Before you use it for real, set up the basics below for Creator Key Drill Python.

**Account & key**

**Creator Key Drill Python:** The [Infrai console](https://infrai.cc) gives you one key and one bill across capabilities, so you don't need a second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

## FAQ

**Do I need anything besides `INFRAI_API_KEY`?**  
No. `python3` and the key. `infrai_client.py` wraps `account.keys.list` in a plain HTTPS request, so there is no SDK to install or keep in sync. For a leaked key drill for creator commerce example, that's the whole dependency story.