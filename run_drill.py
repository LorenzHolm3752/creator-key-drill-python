import argparse
import json

from creator_key_drill import CreatorIncidentRequest, run_creator_key_drill


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the creator leaked-key drill")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--suspected-key-name", required=True)
    parser.add_argument("--leak-marker", required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--subscriber-id", required=True)
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--grace-hours", type=int, default=1)
    args = parser.parse_args()

    request = CreatorIncidentRequest(
        project_id=args.project_id,
        suspected_key_name=args.suspected_key_name,
        leak_marker=args.leak_marker,
        asset_id=args.asset_id,
        subscriber_id=args.subscriber_id,
        content_id=args.content_id,
        grace_hours=args.grace_hours,
    )
    result = run_creator_key_drill(request)
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
