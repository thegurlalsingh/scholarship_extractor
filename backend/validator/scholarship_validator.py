import json
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()


class ScholarshipValidator:


    # TRUSTED OFFICIAL DOMAINS


    TRUSTED_DOMAINS = {
        "scholarships.gov.in": 30,
        "scholarship.up.gov.in": 30,
        "pmsonline.bihar.gov.in": 30,
        "myscheme.gov.in": 30,

        # Major scholarship aggregators.
        # These are trusted as discovery sources,
        # but NOT equivalent to an official government source.
        "buddy4study.com": 15,
        "vidyasaarathi.co.in": 15,
        "scholarships.com": 15,
        "scholars4dev.com": 15,
    }


    # INITIALIZATION


    def __init__(self, timeout=15):

        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            )
        })


    # MAIN VALIDATION


    def validate(self, scholarship: dict) -> dict:

        title = (
            scholarship.get("title")
            or ""
        ).strip()

        source_url = (
            scholarship.get("source_url")
            or ""
        ).strip()

        guidelines_url = (
            scholarship.get("guidelines_url")
            or ""
        ).strip()

        faq_url = (
            scholarship.get("faq_url")
            or ""
        ).strip()

        checks = []

        score = 0


        # 1. TITLE


        if title:

            score += 10

            checks.append({
                "check": "title_present",
                "passed": True,
                "score": 10,
                "message": "Scholarship title is present."
            })

        else:

            checks.append({
                "check": "title_present",
                "passed": False,
                "score": 0,
                "message": "Scholarship title is missing."
            })


        # 2. SOURCE URL


        source_domain = self._extract_domain(
            source_url
        )

        domain_score = self._domain_score(
            source_domain
        )

        score += domain_score

        checks.append({
            "check": "source_domain",
            "passed": domain_score > 0,
            "score": domain_score,
            "domain": source_domain,
            "message": (
                "Trusted scholarship source domain."
                if domain_score >= 30
                else
                "Known scholarship source/aggregator."
                if domain_score > 0
                else
                "Source domain is not in the trusted-domain list."
            )
        })


        # 3. SOURCE URL REACHABILITY


        source_result = self._check_url(
            source_url
        )

        if source_result["reachable"]:

            score += 20

            checks.append({
                "check": "source_reachable",
                "passed": True,
                "score": 20,
                "status_code": source_result["status_code"],
                "final_url": source_result["final_url"],
                "message": "Source URL is reachable."
            })

        else:

            checks.append({
                "check": "source_reachable",
                "passed": False,
                "score": 0,
                "status_code": source_result["status_code"],
                "message": "Source URL could not be verified."
            })


        # 4. GUIDELINES URL


        if guidelines_url:

            guideline_result = self._check_url(
                guidelines_url
            )

            if guideline_result["reachable"]:

                score += 15

                checks.append({
                    "check": "guidelines_reachable",
                    "passed": True,
                    "score": 15,
                    "status_code": guideline_result["status_code"],
                    "message": "Guidelines URL is reachable."
                })

            else:

                checks.append({
                    "check": "guidelines_reachable",
                    "passed": False,
                    "score": 0,
                    "status_code": guideline_result["status_code"],
                    "message": "Guidelines URL could not be verified."
                })

        else:

            checks.append({
                "check": "guidelines_reachable",
                "passed": False,
                "score": 0,
                "message": "No guidelines URL provided."
            })


        # 5. FAQ URL


        if faq_url:

            faq_result = self._check_url(
                faq_url
            )

            if faq_result["reachable"]:

                score += 10

                checks.append({
                    "check": "faq_reachable",
                    "passed": True,
                    "score": 10,
                    "status_code": faq_result["status_code"],
                    "message": "FAQ URL is reachable."
                })

            else:

                checks.append({
                    "check": "faq_reachable",
                    "passed": False,
                    "score": 0,
                    "status_code": faq_result["status_code"],
                    "message": "FAQ URL could not be verified."
                })

        else:

            checks.append({
                "check": "faq_reachable",
                "passed": False,
                "score": 0,
                "message": "No FAQ URL provided."
            })


        # 6. SCHOLARSHIP-TYPE SIGNALS


        if self._looks_like_scholarship(
            title
        ):

            score += 10

            checks.append({
                "check": "scholarship_title_signal",
                "passed": True,
                "score": 10,
                "message": (
                    "Title contains scholarship-related "
                    "terminology."
                )
            })

        else:

            checks.append({
                "check": "scholarship_title_signal",
                "passed": False,
                "score": 0,
                "message": (
                    "Title does not strongly resemble "
                    "a scholarship."
                )
            })


        # 7. DATE VALIDITY


        date_score, date_check = (
            self._validate_dates(
                scholarship
            )
        )

        score += date_score

        checks.append(
            date_check
        )


        # 8. FINAL SCORE


        score = min(
            max(score, 0),
            100
        )

        status = self._get_status(
            score,
            source_domain
        )

        warnings = self._generate_warnings(
            scholarship,
            checks,
            score
        )


        # FINAL JSON RECORD


        return {

            "validation": {

                "status": status,

                "legitimacy_score": score,

                "confidence": round(
                    score / 100,
                    2
                ),

                "verified_at": (
                    datetime.utcnow()
                    .isoformat()
                    + "Z"
                ),

            },

            "scholarship": scholarship,

            "source": {

                "url": source_url,

                "domain": source_domain,

                "is_official_domain": (
                    source_domain in {
                        "scholarships.gov.in",
                        "scholarship.up.gov.in",
                        "pmsonline.bihar.gov.in",
                        "myscheme.gov.in",
                    }
                ),

            },

            "verification_checks": checks,

            "warnings": warnings,

        }


    # BATCH VALIDATION


    def validate_many(
        self,
        scholarships
    ):

        results = []

        for scholarship in scholarships:

            print(
                "[ScholarshipValidator] "
                f"Validating: "
                f"{scholarship.get('title', '')}"
            )

            result = self.validate(
                scholarship
            )

            results.append(
                result
            )

        return results


    # SAVE JSON


    @staticmethod
    def save_json(
        results,
        output_file="validated_scholarships.json"
    ):

        payload = {

            "generated_at": (
                datetime.utcnow()
                .isoformat()
                + "Z"
            ),

            "total_scholarships": len(
                results
            ),

            "scholarships": results,

        }

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                payload,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(
            "[ScholarshipValidator] "
            f"Saved {len(results)} scholarships "
            f"to {output_file}"
        )


    # URL CHECK


    def _check_url(
        self,
        url
    ):

        if not url:

            return {
                "reachable": False,
                "status_code": None,
                "final_url": None,
            }

        # Prevent invalid generated URLs such as /null.
        if url.rstrip("/").lower().endswith(
            "/null"
        ):

            return {
                "reachable": False,
                "status_code": None,
                "final_url": url,
            }

        try:

            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                stream=True
            )

            reachable = (
                200
                <= response.status_code
                < 400
            )

            final_url = response.url

            response.close()

            return {
                "reachable": reachable,
                "status_code": response.status_code,
                "final_url": final_url,
            }

        except requests.RequestException:

            return {
                "reachable": False,
                "status_code": None,
                "final_url": None,
            }


    # DOMAIN SCORE


    def _domain_score(
        self,
        domain
    ):

        if domain in self.TRUSTED_DOMAINS:

            return self.TRUSTED_DOMAINS[
                domain
            ]

        return 0


    # DOMAIN EXTRACTION


    @staticmethod
    def _extract_domain(url):

        try:

            domain = urlparse(
                url
            ).netloc.lower()

            if domain.startswith(
                "www."
            ):
                domain = domain[4:]

            domain = domain.split(":")[0]

            return domain

        except Exception:

            return ""


    # SCHOLARSHIP SIGNAL


    @staticmethod
    def _looks_like_scholarship(
        title
    ):

        keywords = (
            "scholarship",
            "fellowship",
            "financial assistance",
            "education support",
            "student support",
            "stipend",
            "merit scheme",
        )

        title = title.lower()

        return any(
            keyword in title
            for keyword in keywords
        )


    # DATE VALIDATION


    @staticmethod
    def _validate_dates(
        scholarship
    ):

        start = (
            scholarship.get(
                "application_start"
            )
        )

        end = (
            scholarship.get(
                "application_end"
            )
        )

        if not start and not end:

            return (
                0,
                {
                    "check": "application_dates",
                    "passed": False,
                    "score": 0,
                    "message": (
                        "Application dates are missing."
                    )
                }
            )

        if start and end:

            try:

                start_date = datetime.strptime(
                    start,
                    "%d-%m-%Y"
                )

                end_date = datetime.strptime(
                    end,
                    "%d-%m-%Y"
                )

                if start_date <= end_date:

                    return (
                        5,
                        {
                            "check": "application_dates",
                            "passed": True,
                            "score": 5,
                            "message": (
                                "Application date range is valid."
                            )
                        }
                    )

                return (
                    0,
                    {
                        "check": "application_dates",
                        "passed": False,
                        "score": 0,
                        "message": (
                            "Application start date "
                            "is after end date."
                        )
                    }
                )

            except ValueError:

                return (
                    0,
                    {
                        "check": "application_dates",
                        "passed": False,
                        "score": 0,
                        "message": (
                            "Application dates have "
                            "an invalid format."
                        )
                    }
                )

        return (
            0,
            {
                "check": "application_dates",
                "passed": False,
                "score": 0,
                "message": (
                    "Only one application date "
                    "was provided."
                )
            }
        )


    # STATUS


    @staticmethod
    def _get_status(
        score,
        source_domain
    ):

        if (
            source_domain in {
                "scholarships.gov.in",
                "scholarship.up.gov.in",
                "pmsonline.bihar.gov.in",
                "myscheme.gov.in",
            }
            and score >= 80
        ):

            return "VERIFIED"

        if score >= 80:
            return "HIGH_CONFIDENCE"

        if score >= 60:
            return "LIKELY_VALID"

        if score >= 40:
            return "NEEDS_REVIEW"

        return "LOW_CONFIDENCE"


    # WARNINGS


    @staticmethod
    def _generate_warnings(
        scholarship,
        checks,
        score
    ):

        warnings = []

        guidelines_url = (
            scholarship.get(
                "guidelines_url"
            )
            or ""
        )

        faq_url = (
            scholarship.get(
                "faq_url"
            )
            or ""
        )

        if not guidelines_url:

            warnings.append(
                "Guidelines URL is missing."
            )

        if not faq_url:

            warnings.append(
                "FAQ URL is missing."
            )

        if (
            guidelines_url.rstrip("/")
            .lower()
            .endswith("/null")
        ):

            warnings.append(
                "Guidelines URL is invalid."
            )

        if (
            faq_url.rstrip("/")
            .lower()
            .endswith("/null")
        ):

            warnings.append(
                "FAQ URL is invalid."
            )

        if not scholarship.get(
            "application_start"
        ):

            warnings.append(
                "Application start date is missing."
            )

        if not scholarship.get(
            "application_end"
        ):

            warnings.append(
                "Application end date is missing."
            )

        if score < 60:

            warnings.append(
                "Scholarship requires manual verification."
            )

        return warnings