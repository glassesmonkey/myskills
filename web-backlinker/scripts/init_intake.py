#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import load_json, now_iso, save_json


REQUIRED_FIELDS = [
    "product_name",
    "canonical_url",
    "one_liner",
    "short_description",
    "medium_description",
    "category_primary",
    "target_audience",
    "use_cases",
    "submitter_name",
    "primary_email",
    "company_email",
    "preferred_verification_email",
    "allow_gmail_signup",
    "allow_company_email_signup",
    "allow_oauth_login",
    "allow_manual_captcha",
    "allow_paid_listing",
    "allow_reciprocal_backlink",
    "allow_founder_identity_disclosure",
    "allow_phone_disclosure",
    "allow_address_disclosure",
]

RECOMMENDED_FIELDS = [
    "company_name",
    "founder_name",
    "founding_year",
    "launch_date",
    "based_in_country",
    "pricing_url",
    "privacy_url",
    "logo_url",
    "screenshot_url",
    "markets",
]

BOOLEAN_FIELDS = {
    "allow_gmail_signup",
    "allow_company_email_signup",
    "allow_oauth_login",
    "allow_manual_captcha",
    "allow_paid_listing",
    "allow_reciprocal_backlink",
    "allow_founder_identity_disclosure",
    "allow_phone_disclosure",
    "allow_address_disclosure",
}

LIST_FIELDS = {"use_cases", "markets"}
BOOLEAN_TRUE = {"true", "1", "yes", "y", "是", "允许", "可以", "可", "能", "同意", "接受"}
BOOLEAN_FALSE = {"false", "0", "no", "n", "否", "不允许", "不可以", "不可", "不能", "拒绝", "不接受"}

FIELD_META = {
    "category_primary": {
        "label_zh": "产品主要分类",
        "question_zh": "这个产品最适合归到什么主分类？比如 AI 音乐生成、AI 音频工具、音乐创作工具。",
        "example": "AI 音乐生成",
    },
    "target_audience": {
        "label_zh": "主要用户",
        "question_zh": "这个产品主要给谁用？比如 音乐创作者、短视频创作者、营销团队、普通用户。",
        "example": "音乐创作者、短视频创作者",
    },
    "use_cases": {
        "label_zh": "典型用途",
        "question_zh": "用户一般会拿它做什么？写 2 到 5 个典型场景即可。",
        "example": "生成原创歌曲, 制作短视频配乐, 写广告 jingles",
    },
    "submitter_name": {
        "label_zh": "提交署名",
        "question_zh": "提交目录站时，应该用谁的名字作为提交人？",
        "example": "Alex",
    },
    "allow_gmail_signup": {
        "label_zh": "是否允许用 Gmail 注册",
        "question_zh": "如果某个站点只能用 Gmail 注册，是否允许系统继续？",
        "example": "允许",
    },
    "allow_company_email_signup": {
        "label_zh": "是否允许用公司邮箱注册",
        "question_zh": "如果站点支持公司域名邮箱注册，是否允许优先用公司邮箱？",
        "example": "允许",
    },
    "allow_oauth_login": {
        "label_zh": "是否允许 OAuth 登录",
        "question_zh": "如果站点要求 Google / GitHub OAuth 登录，是否允许继续？",
        "example": "允许",
    },
    "allow_manual_captcha": {
        "label_zh": "是否允许人工接手验证码/浏览器",
        "question_zh": "如果遇到验证码或需要人工点一下真实浏览器，是否允许转人工继续？",
        "example": "不允许",
    },
    "allow_paid_listing": {
        "label_zh": "是否允许付费收录",
        "question_zh": "如果目录站要求付费才能发布，是否允许继续？",
        "example": "不允许",
    },
    "allow_reciprocal_backlink": {
        "label_zh": "是否允许互链",
        "question_zh": "如果站点要求先给对方加友情链接，是否允许继续？",
        "example": "不允许",
    },
    "allow_founder_identity_disclosure": {
        "label_zh": "是否允许披露创始人身份",
        "question_zh": "如果站点要求填写创始人姓名或身份，是否允许披露？",
        "example": "不允许",
    },
    "allow_phone_disclosure": {
        "label_zh": "是否允许填写电话",
        "question_zh": "如果站点要求填写手机号或联系电话，是否允许披露？",
        "example": "不允许",
    },
    "allow_address_disclosure": {
        "label_zh": "是否允许填写地址",
        "question_zh": "如果站点要求填写公司地址或所在地，是否允许披露？",
        "example": "不允许",
    },
}


def infer_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    facts = profile.get("facts", {}) or {}
    materials = profile.get("materials", {}) or {}
    contact_emails = facts.get("contact_emails", []) or []
    return {
        "product_name": profile.get("product_name", ""),
        "canonical_url": profile.get("canonical_url") or profile.get("promoted_url", ""),
        "one_liner": profile.get("one_liner", ""),
        "short_description": profile.get("short_description", ""),
        "medium_description": profile.get("medium_description", ""),
        "primary_email": contact_emails[0] if contact_emails else "",
        "company_email": contact_emails[0] if contact_emails else "",
        "preferred_verification_email": contact_emails[0] if contact_emails else "",
        "pricing_url": facts.get("pricing_url", ""),
        "privacy_url": facts.get("privacy_url", ""),
        "markets": materials.get("category_hints", [])[:5],
    }


def default_template() -> dict[str, Any]:
    template = {field: "" for field in REQUIRED_FIELDS + RECOMMENDED_FIELDS}
    for field in BOOLEAN_FIELDS:
        template[field] = None
    for field in LIST_FIELDS:
        template[field] = []
    return template


def parse_value(key: str, value: str) -> Any:
    if key in BOOLEAN_FIELDS:
        lowered = value.strip().lower()
        if lowered in BOOLEAN_TRUE:
            return True
        if lowered in BOOLEAN_FALSE:
            return False
        raise SystemExit(f"invalid boolean for {key}: {value}")
    if key in LIST_FIELDS:
        normalized = value.replace("，", ",").replace("、", ",").replace("\n", ",")
        return [item.strip() for item in normalized.split(",") if item.strip()]
    return value.strip()


def merge_non_empty(base: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in fresh.items():
        if value in ("", None, []):
            continue
        merged[key] = value
    return merged


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def build_friendly_questions(required_missing: list[str]) -> list[dict[str, str]]:
    questions = []
    for field in required_missing:
        meta = FIELD_META.get(
            field,
            {
                "label_zh": field,
                "question_zh": f"请提供 {field}。",
                "example": "",
            },
        )
        questions.append(
            {
                "field": field,
                "label_zh": meta["label_zh"],
                "question_zh": meta["question_zh"],
                "example": meta["example"],
            }
        )
    return questions


def build_reply_template_zh(required_missing: list[str]) -> list[str]:
    lines = ["请直接按下面这份中文模板回复我，缺的项填上就可以："]
    for item in build_friendly_questions(required_missing):
        suffix = f"（例如：{item['example']}）" if item["example"] else ""
        lines.append(f"- {item['label_zh']}：{suffix}".rstrip("："))
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect and validate promoted-site intake before real submission workers run.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--from-file", default="")
    parser.add_argument("--set", action="append", default=[])
    parser.add_argument("--print-template", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_json(manifest_path, {})
    if not manifest:
        raise SystemExit(f"manifest not found: {manifest_path}")

    paths = manifest.get("paths", {})
    profile_path = Path(paths["profile_path"]).expanduser().resolve()
    intake_path = Path(paths.get("intake_path") or profile_path.with_suffix(".intake.json")).expanduser().resolve()

    template = default_template()
    if args.print_template:
        print(json.dumps(template, ensure_ascii=False, indent=2))
        return 0

    existing = load_json(intake_path, template)
    profile = load_json(profile_path, {})
    merged = merge_non_empty(template, infer_from_profile(profile))
    merged = merge_non_empty(merged, existing)

    if args.from_file:
        merged = merge_non_empty(merged, load_json(Path(args.from_file).expanduser().resolve(), {}))

    for item in args.set:
        if "=" not in item:
            raise SystemExit(f"invalid --set payload: {item}")
        key, raw_value = item.split("=", 1)
        merged[key.strip()] = parse_value(key.strip(), raw_value)

    required_missing = [field for field in REQUIRED_FIELDS if is_missing(merged.get(field))]
    recommended_missing = [field for field in RECOMMENDED_FIELDS if is_missing(merged.get(field))]
    suggested_prompt = [
        "Please provide the missing initialization fields before I scout or submit any targets:",
        *[f"- {field}:" for field in required_missing],
    ] if required_missing else []
    friendly_questions_zh = build_friendly_questions(required_missing)
    reply_template_zh = build_reply_template_zh(required_missing) if required_missing else []
    operator_message_zh = (
        "当前还缺少一些提交前必须确认的信息。我先不继续侦察或提交，避免系统擅自猜测。"
        if required_missing
        else ""
    )

    payload = {
        **template,
        **merged,
        "required_missing": required_missing,
        "recommended_missing": recommended_missing,
        "suggested_prompt": suggested_prompt,
        "friendly_questions_zh": friendly_questions_zh,
        "reply_template_zh": reply_template_zh,
        "updated_at": now_iso(),
    }
    save_json(intake_path, payload)

    manifest.setdefault("intake", {})
    manifest["intake"]["path"] = str(intake_path)
    manifest["intake"]["required_missing"] = required_missing
    manifest["intake"]["recommended_missing"] = recommended_missing
    manifest["intake"]["updated_at"] = payload["updated_at"]
    manifest["status"] = "WAITING_CONFIG" if required_missing else "READY"
    manifest["updated_at"] = payload["updated_at"]
    save_json(manifest_path, manifest)

    print(
        json.dumps(
            {
                "ok": True,
                "manifest_path": str(manifest_path),
                "intake_path": str(intake_path),
                "status": manifest["status"],
                "required_missing": required_missing,
                "recommended_missing": recommended_missing,
                "next_questions": required_missing[:8],
                "suggested_prompt": suggested_prompt,
                "friendly_questions_zh": friendly_questions_zh,
                "reply_template_zh": reply_template_zh,
                "operator_message_zh": operator_message_zh,
                "intake": payload,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
