import json
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()



OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "liquid/lfm-2.5-2.6b:free"


class ScholarshipExtractor:

    def __init__(self):

        # Read key from environment - NEVER hardcode API keys in source.
        import os

        self.api_key = os.environ.get("OPENROUTER_API_KEY")

        if not self.api_key:
            print(
                "[ScholarshipExtractor] "
                "WARNING: OPENROUTER_API_KEY not found."
            )


    # MAIN


    def extract(self, page: dict, use_llm_fallback: bool = True):
        """
        use_llm_fallback:
            True  - if deterministic extraction finds nothing, ask the LLM
                    (use for SCHOLARSHIP_LISTING pages, which are rare -
                    typically one per site).
            False - deterministic extraction only, return [] if it finds
                    nothing (use for SCHOLARSHIP_DETAIL pages, which can be
                    numerous per crawl and where a weak free-tier LLM has
                    nothing but nav/boilerplate text to hallucinate from).
        """

        html = page.get("html", "")
        source_url = page.get("url", "")

        if not html:
            return []

        # ------------------------------------------------------
        # 1. Try deterministic extraction
        # ------------------------------------------------------

        candidates = self._find_candidate_containers(
            html
        )

        print(
            f"[ScholarshipExtractor] "
            f"Deterministic candidates: "
            f"{len(candidates)}"
        )

        deterministic_results = []

        for candidate in candidates:

            scholarship = self._extract_deterministic(
                candidate,
                source_url
            )

            if scholarship:
                deterministic_results.append(
                    scholarship
                )

        deterministic_results = self._deduplicate(
            deterministic_results
        )

        # ------------------------------------------------------
        # 2. If deterministic extraction worked
        # ------------------------------------------------------

        if deterministic_results:

            print(
                f"[ScholarshipExtractor] "
                f"Deterministic extraction returned "
                f"{len(deterministic_results)}."
            )

            return deterministic_results

        # ------------------------------------------------------
        # 3. FALLBACK → LLM (only if the caller allows it)
        # ------------------------------------------------------

        print(
            "[ScholarshipExtractor] "
            "Deterministic extraction returned 0."
        )

        if not use_llm_fallback:

            print(
                "[ScholarshipExtractor] "
                "LLM fallback disabled for this page type - returning []."
            )

            return []

        print(
            "[ScholarshipExtractor] "
            "Using OpenRouter LLM..."
        )

        return self._llm_extract(
            html,
            source_url
        )


    # CANDIDATE DETECTION


    def _find_candidate_containers(
        self,
        html: str
    ):

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        candidates = []

        # ------------------------------------------------------
        # Strategy 1:
        # Search for text nodes containing application dates.
        # ------------------------------------------------------

        date_nodes = soup.find_all(
            string=re.compile(
                r"Student\s+Application\s+Open\s+till",
                re.IGNORECASE
            )
        )

        print(
            f"[ScholarshipExtractor] "
            f"Found {len(date_nodes)} "
            f"application-date nodes"
        )

        for node in date_nodes:

            current = node.parent

            # Walk upwards until we find a meaningful block.
            for _ in range(8):

                if current is None:
                    break

                text = self._normalize_ws(
                    current.get_text(
                        " ",
                        strip=True
                    )
                )

                # A scholarship card normally contains:
                #
                # title
                # scheme open date
                # application date
                #
                if (
                    "Student Application Open till"
                    in text
                    and
                    "Scheme Open from"
                    in text
                    and
                    len(text) < 5000
                ):

                    candidates.append(
                        current
                    )

                    break

                current = current.parent

        # ------------------------------------------------------
        # Strategy 2:
        # Search for "Scheme Open from"
        # ------------------------------------------------------

        if not candidates:

            scheme_nodes = soup.find_all(
                string=re.compile(
                    r"Scheme\s+Open\s+from",
                    re.IGNORECASE
                )
            )

            print(
                f"[ScholarshipExtractor] "
                f"Found {len(scheme_nodes)} "
                f"'Scheme Open from' nodes"
            )

            for node in scheme_nodes:

                current = node.parent

                for _ in range(8):

                    if current is None:
                        break

                    text = self._normalize_ws(
                        current.get_text(
                            " ",
                            strip=True
                        )
                    )

                    if (
                        "Scheme Open from"
                        in text
                        and
                        len(text) < 5000
                    ):

                        candidates.append(
                            current
                        )

                        break

                    current = current.parent

        # ------------------------------------------------------
        # Remove duplicates
        # ------------------------------------------------------

        unique = []

        seen = set()

        for candidate in candidates:

            text = candidate.get_text(
                " ",
                strip=True
            )

            key = text[:1000]

            if key in seen:
                continue

            seen.add(key)

            unique.append(candidate)

        return unique


    # DETERMINISTIC EXTRACTION


    def _extract_deterministic(
        self,
        container,
        source_url
    ):

        text = self._normalize_ws(
            container.get_text(
                " ",
                strip=True
            )
        )

        if not self._has_application_information(
            text
        ):
            return None

        title = self._extract_title(
            container
        )

        if not title:
            return None

        return {
            "title": title,

            "source_url": source_url,

            "organization":
                self._extract_organization(
                    text
                ),

            "scheme_type":
                self._extract_scheme_type(
                    text
                ),

            "application_start":
                self._extract_date(
                    text,
                    "Scheme Open from"
                ),

            "application_end":
                self._extract_date(
                    text,
                    "Student Application Open till"
                ),

            "guidelines_url":
                self._find_link(
                    container,
                    (
                        "specification",
                        "guideline",
                        "guidelines",
                    ),
                    source_url
                ),

            "faq_url":
                self._find_link(
                    container,
                    (
                        "faq",
                        "frequently asked",
                    ),
                    source_url
                ),

            # Extended schema fields — deterministic where possible,
            # None otherwise. NEVER guess a value.
            "application_url":
                self._find_link(
                    container,
                    (
                        "apply now",
                        "apply online",
                        "register",
                        "application form",
                        "apply here",
                    ),
                    source_url
                ),

            "scholarship_amount":
                self._extract_amount(text),

            "education_level":
                self._extract_education_level(text),

            "income_criteria":
                self._extract_income_criteria(text),

            "gender_criteria":
                self._extract_gender_criteria(text),

            "category_criteria":
                self._extract_category_criteria(text),

            "domicile":
                self._extract_domicile(text),

            "eligibility_summary": None,
            "documents_required": None,
            "selection_process": None,
        }


    # TITLE


    @staticmethod
    def _extract_title(container):

        # First try headings
        heading = container.find(
            [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
            ]
        )

        if heading:

            title = heading.get_text(
                " ",
                strip=True
            )

            if (
                "scholarship"
                in title.lower()
                or
                "scheme"
                in title.lower()
                or
                "fellowship"
                in title.lower()
            ):

                return title

        # ------------------------------------------------------
        # Fallback:
        # Search text lines
        # ------------------------------------------------------

        text = container.get_text(
            "\n",
            strip=True
        )

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        for line in lines:

            lower = line.lower()

            if (
                "scholarship"
                in lower
                or
                "fellowship"
                in lower
            ):

                if len(line) < 500:

                    return line

        return None


    # WHITESPACE NORMALIZATION


    @staticmethod
    def _normalize_ws(text):

        # The source HTML has inconsistent inline whitespace, e.g.
        # "Scheme  Open from" (double space) and
        # "Student Application  Open till". Collapse all runs of
        # whitespace to a single space so substring/regex matches
        # against expected single-spaced labels work reliably.

        return re.sub(r"\s+", " ", text).strip()


    # APPLICATION INFO


    @staticmethod
    def _has_application_information(text):

        lower = text.lower()

        return (
            "scheme open from" in lower
            and
            (
                "student application open till"
                in lower
            )
        )


    # ORGANIZATION


    @staticmethod
    def _extract_organization(text):

        organizations = (
            "AICTE",
            "UGC",
            "Ministry of Home Affairs",
            "Ministry of Railways",
            "Ministry of Tribal Affairs",
            "Ministry of Labour & Employment",
            "Ministry of New And Renewable Energy",
            "Ministry of Statistics and Programme Implementation",
            "Department of Agriculture Research and Education",
            "Department of Higher Education",
            "Department of School Education & Literacy",
            "Department of Social Justice & Empowerment",
            "Department of Empowerment of Persons with Disabilities",
            "North Eastern Council",
        )

        lower = text.lower()

        for organization in organizations:

            if organization.lower() in lower:

                return organization

        return None


    # SCHEME TYPE


    @staticmethod
    def _extract_scheme_type(text):

        lower = text.lower()

        if "merit based scheme" in lower:
            return "MERIT_BASED"

        if "welfare based scheme" in lower:
            return "WELFARE_BASED"

        return None


    # SCHOLARSHIP AMOUNT


    @staticmethod
    def _extract_amount(text):
        """
        Extracts scholarship amount/benefit string.
        Returns the first money mention found, or None.
        Examples matched: ₹50,000 | Rs. 25000 | INR 10,000 | 50000 per annum
        NEVER guesses — returns None if no amount found.
        """
        patterns = [
            r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\s*(?:per\s+annum|per\s+month|p\.?a\.?|p\.?m\.?|lakh))?",
            r"[\d,]+\s*(?:per\s+annum|per\s+month)\s*(?:stipend|scholarship|grant|award)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None


    # EDUCATION LEVEL


    @staticmethod
    def _extract_education_level(text):
        """
        Extracts the academic level the scholarship is for.
        Returns a normalized string or None — never guessed.
        """
        lower = text.lower()
        if any(k in lower for k in ("post doctoral", "post-doctoral", "postdoctoral")):
            return "Post-Doctoral"
        if any(k in lower for k in ("phd", "ph.d", "doctoral")):
            return "PhD / Doctoral"
        if any(k in lower for k in ("post graduate", "post-graduate", "postgraduate", "pg ", "masters", "m.tech", "mca", "mba")):
            return "Post Graduate"
        if any(k in lower for k in ("undergraduate", "under graduate", "ug ", "b.tech", "btech", "b.e.", "bsc", "ba ", "bcom", "degree course")):
            return "Under Graduate"
        if any(k in lower for k in ("diploma", "polytechnic")):
            return "Diploma"
        if any(k in lower for k in ("pre matric", "pre-matric", "class 9", "class 10", "class ix", "class x")):
            return "Pre-Matric"
        if any(k in lower for k in ("post matric", "post-matric", "class 11", "class 12", "class xi", "class xii")):
            return "Post-Matric"
        return None


    # INCOME CRITERIA


    @staticmethod
    def _extract_income_criteria(text):
        """
        Extracts income/family income criteria if stated on the page.
        Returns verbatim extracted text or None.
        NEVER invents a value — if not present, returns None.
        """
        patterns = [
            r"(?:family\s+)?income\s+(?:not\s+exceeding|below|up\s+to|less\s+than)\s+[₹Rs\.INR\s]*[\d,\.]+\s*(?:lakh|lakhs|per\s+annum|p\.?a\.?)?",
            r"annual\s+income\s+(?:limit|criteria|should\s+be)?\s*[:]?\s*[₹Rs\.INR\s]*[\d,\.]+\s*(?:lakh|lakhs)?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None


    # GENDER CRITERIA


    @staticmethod
    def _extract_gender_criteria(text):
        """
        Extracts gender restriction if stated. Returns string or None.
        """
        lower = text.lower()
        if "girl students" in lower or "female students" in lower or "women students" in lower:
            return "Female / Girl Students only"
        if "male students" in lower or "boy students" in lower:
            return "Male Students only"
        return None


    # CATEGORY CRITERIA


    @staticmethod
    def _extract_category_criteria(text):
        """
        Extracts caste/reservation category criteria if stated.
        Returns a comma-joined string of found categories, or None.
        """
        lower = text.lower()
        found = []
        if "scheduled caste" in lower or " sc " in lower or "(sc)" in lower:
            found.append("SC")
        if "scheduled tribe" in lower or " st " in lower or "(st)" in lower:
            found.append("ST")
        if "other backward" in lower or " obc " in lower or "(obc)" in lower:
            found.append("OBC")
        if "minority" in lower or "muslim" in lower or "christian" in lower or "sikh" in lower:
            found.append("Minority")
        if "economically weaker" in lower or " ews " in lower or "(ews)" in lower:
            found.append("EWS")
        if "divyang" in lower or "disabled" in lower or "specially abled" in lower or "handicapped" in lower:
            found.append("Persons with Disabilities")
        if not found:
            # Only return if there's an explicit general signal
            if "all category" in lower or "open category" in lower or "general category" in lower:
                return "All Categories"
            return None
        return ", ".join(found)


    # DOMICILE


    @staticmethod
    def _extract_domicile(text):
        """
        Extracts domicile / state requirement if stated.
        Returns string or None.
        """
        lower = text.lower()
        # Central government scholarships are open to all India
        if "national scholarship" in lower or "central sector" in lower or "all india" in lower:
            return "All India"
        # State-specific signals
        states = [
            "uttar pradesh", "maharashtra", "karnataka", "tamil nadu",
            "andhra pradesh", "telangana", "rajasthan", "gujarat",
            "west bengal", "bihar", "madhya pradesh", "kerala", "punjab",
            "haryana", "odisha", "jharkhand", "assam", "chhattisgarh",
            "uttarakhand", "himachal pradesh", "jammu", "kashmir", "goa",
        ]
        for state in states:
            if state in lower:
                return state.title()
        return None


    # DATE


    @staticmethod
    def _extract_date(
        text,
        label
    ):

        # Build a whitespace-flexible pattern from the label so
        # inconsistent spacing in the source HTML (e.g. "Scheme  Open
        # from") doesn't break the match.
        label_pattern = r"\s+".join(
            re.escape(word) for word in label.split()
        )

        pattern = (
            label_pattern
            + r"\s*:?\s*"
            + r"(\d{2}-\d{2}-\d{4})"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1)

        return None


    # LINKS


    @staticmethod
    def _find_link(
        container,
        keywords,
        base_url
    ):

        for link in container.find_all(
            "a",
            href=True
        ):

            text = link.get_text(
                " ",
                strip=True
            ).lower()

            href = link.get(
                "href",
                ""
            ).lower()

            combined = (
                f"{text} {href}"
            )

            if any(
                keyword.lower()
                in combined
                for keyword in keywords
            ):

                return urljoin(
                    base_url,
                    link.get("href")
                )

        return None


    # LLM EXTRACTION


    def _llm_extract(
        self,
        html,
        source_url
    ):

        if not self.api_key:

            print(
                "[ScholarshipExtractor] "
                "No OpenRouter API key."
            )

            return []

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # Remove unnecessary content.
        for tag in soup([
            "script",
            "style",
            "noscript",
            "svg"
        ]):

            tag.decompose()

        text = soup.get_text(
            " ",
            strip=True
        )

        # ------------------------------------------------------
        # IMPORTANT
        #
        # Do NOT send the entire page.
        #
        # Keep only the scholarship-related section.
        # ------------------------------------------------------

        text = self._extract_relevant_text(
            text
        )

        # Keep prompt safely bounded.
        text = text[:18000]

        prompt = f"""
You are extracting scholarship information from a government scholarship portal.

Extract EVERY scholarship/scheme visible in the provided text.

Return ONLY valid JSON. Do not use markdown. Do not use ```.

Return exactly this structure:

[
  {{
    "title": "string",
    "organization": "string or null",
    "scheme_type": "MERIT_BASED or WELFARE_BASED or null",
    "application_start": "DD-MM-YYYY or null",
    "application_end": "DD-MM-YYYY or null",
    "guidelines_url": "full URL or null",
    "faq_url": "full URL or null",
    "application_url": "full URL to apply or null",
    "scholarship_amount": "e.g. Rs. 50000 per annum or null",
    "education_level": "Under Graduate / Post Graduate / Diploma / Pre-Matric / Post-Matric / PhD or null",
    "income_criteria": "verbatim income limit from page or null",
    "gender_criteria": "Female only / Male only or null",
    "category_criteria": "SC, ST, OBC etc. or null",
    "domicile": "state name or All India or null"
  }}
]

CRITICAL RULES:
1. Each scholarship/scheme must be a separate object.
2. NEVER invent or guess any field. If you cannot find the value on the page, use null.
3. Do not hallucinate income limits, amounts, or eligibility criteria.
4. Preserve scholarship names exactly as they appear.
5. The source page URL is: {source_url}

TEXT:
{text}
"""

        print(
            "[ScholarshipExtractor] "
            f"Calling OpenRouter model: "
            f"{OPENROUTER_MODEL}"
        )

        try:

            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization":
                        f"Bearer {self.api_key}",
                    "Content-Type":
                        "application/json",
                },
                json={
                    "model":
                        OPENROUTER_MODEL,

                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],

                    "temperature": 0,

                    # Prevent huge/truncated output.
                    "max_tokens": 6000,
                },

                timeout=90
            )

            response.raise_for_status()

            data = response.json()

            if "error" in data:
                print(
                    "[ScholarshipExtractor] "
                    f"OpenRouter returned an error: {data['error']}"
                )
                return []

            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content")
            )

            if not content:
                print(
                    "[ScholarshipExtractor] "
                    "OpenRouter returned empty content "
                    f"(full response: {data})"
                )
                return []

            parsed = self._parse_json(
                content
            )

            if not isinstance(
                parsed,
                list
            ):

                print(
                    "[ScholarshipExtractor] "
                    "LLM response was not a list."
                )

                return []

            results = []

            for item in parsed:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                title = str(
                    item.get(
                        "title",
                        ""
                    )
                ).strip()

                if not title:
                    continue

                results.append({

                    "title": title,
                    "source_url": source_url,
                    "organization": item.get("organization"),
                    "scheme_type": item.get("scheme_type"),
                    "application_start": item.get("application_start"),
                    "application_end": item.get("application_end"),
                    "guidelines_url": item.get("guidelines_url"),
                    "faq_url": item.get("faq_url"),
                    # Extended schema — null is correct when LLM didn't find it
                    "application_url": item.get("application_url"),
                    "scholarship_amount": item.get("scholarship_amount"),
                    "education_level": item.get("education_level"),
                    "income_criteria": item.get("income_criteria"),
                    "gender_criteria": item.get("gender_criteria"),
                    "category_criteria": item.get("category_criteria"),
                    "domicile": item.get("domicile"),
                    "eligibility_summary": None,
                    "documents_required": None,
                    "selection_process": None,
                })

            results = self._deduplicate(
                results
            )

            print(
                f"[ScholarshipExtractor] "
                f"LLM extracted "
                f"{len(results)} scholarships."
            )

            return results

        except requests.RequestException as e:

            print(
                "[ScholarshipExtractor] "
                f"OpenRouter request failed: {e}"
            )

            return []

        except Exception as e:

            print(
                "[ScholarshipExtractor] "
                f"LLM extraction failed: {e}"
            )

            return []


    # RELEVANT TEXT


    @staticmethod
    def _extract_relevant_text(text):

        lower = text.lower()

        # Try starting near "Schemes On NSP".
        markers = (
            "schemes on nsp",
            "central sector scheme",
            "schemes on nsp ministry",
        )

        start = -1

        for marker in markers:

            position = lower.find(
                marker
            )

            if position != -1:

                start = position

                break

        if start == -1:

            return text[:18000]

        return text[start:start + 18000]


    # JSON PARSER


    @staticmethod
    def _parse_json(content):

        content = content.strip()

        # ------------------------------------------------------
        # Remove markdown fences
        # ------------------------------------------------------

        content = re.sub(
            r"^```json\s*",
            "",
            content,
            flags=re.IGNORECASE
        )

        content = re.sub(
            r"^```\s*",
            "",
            content
        )

        content = re.sub(
            r"\s*```$",
            "",
            content
        )

        content = content.strip()

        # ------------------------------------------------------
        # Direct parse
        # ------------------------------------------------------

        try:

            return json.loads(
                content
            )

        except json.JSONDecodeError:
            pass

        # ------------------------------------------------------
        # Try extracting first JSON array
        # ------------------------------------------------------

        start = content.find("[")

        end = content.rfind("]")

        if (
            start != -1
            and end != -1
            and end > start
        ):

            candidate = content[
                start:end + 1
            ]

            try:

                return json.loads(
                    candidate
                )

            except json.JSONDecodeError:
                pass

        print(
            "[ScholarshipExtractor] "
            "Could not parse LLM JSON."
        )

        return []


    # DEDUPLICATION


    @staticmethod
    def _deduplicate(
        scholarships
    ):

        seen = set()

        result = []

        for scholarship in scholarships:

            title = (
                scholarship
                .get("title", "")
                .strip()
                .lower()
            )

            if not title:
                continue

            if title in seen:
                continue

            seen.add(title)

            result.append(
                scholarship
            )

        return result