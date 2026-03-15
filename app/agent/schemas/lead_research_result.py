from dataclasses import dataclass
from typing import Optional


@dataclass
class FieldResult:
    value:      Optional[str]   # extracted value, None if not found
    confidence: str             # 'High' | 'Medium' | 'Low' | 'Not Found'
    source:     Optional[str]   # URL or source description

    def to_dict(self) -> dict:
        return {
            'value':      self.value,
            'confidence': self.confidence,
            'source':     self.source,
        }


@dataclass
class LeadResearchResult:
    # ── Core lead form fields (map 1:1 to leads table columns) ───────────────
    company_name:  FieldResult   # leads.company_name
    contact_name:  FieldResult   # leads.contact
    contact_title: FieldResult   # supplemental — appended to leads.contact
    phone:         FieldResult   # leads.number
    email:         FieldResult   # leads.email
    address:       FieldResult   # leads.address
    sq_footage:    FieldResult   # leads.sq_ft (numeric)
    potential_roi: FieldResult   # leads.potential (annual savings as numeric USD)
    annual_sales:  FieldResult   # leads.annual_sales_locations
    notes:         FieldResult   # leads.new_note (synthesized summary)
    facility_type: FieldResult   # leads.targets

    # ── Extended intelligence (Research Summary panel only) ───────────────────
    employee_count:     FieldResult
    other_locations:    FieldResult
    annual_kwh_savings: FieldResult
    payback_period:     FieldResult
    website_url:        FieldResult
    linkedin_url:       FieldResult
    recent_news:        FieldResult

    # ── Agent metadata ────────────────────────────────────────────────────────
    agent_run_id:       str
    total_searches:     int
    total_urls_fetched: int
    tokens_used:        int
    run_duration_sec:   float
    raw_json:           str
    status:             str             # 'success' | 'partial' | 'timeout' | 'error'
    error_message:      Optional[str]

    def to_form_dict(self) -> dict:
        """Returns only the fields that map directly to Add Lead form inputs."""
        return {
            'company_name':  self.company_name.to_dict(),
            'contact_name':  self.contact_name.to_dict(),
            'phone':         self.phone.to_dict(),
            'email':         self.email.to_dict(),
            'address':       self.address.to_dict(),
            'sq_footage':    self.sq_footage.to_dict(),
            'potential_roi': self.potential_roi.to_dict(),
            'annual_sales':  self.annual_sales.to_dict(),
            'notes':         self.notes.to_dict(),
            'facility_type': self.facility_type.to_dict(),
        }

    def to_extended_dict(self) -> dict:
        """Returns extended intelligence for the Research Summary panel."""
        return {
            'contact_title':     self.contact_title.to_dict(),
            'employee_count':    self.employee_count.to_dict(),
            'other_locations':   self.other_locations.to_dict(),
            'annual_kwh_savings':self.annual_kwh_savings.to_dict(),
            'payback_period':    self.payback_period.to_dict(),
            'website_url':       self.website_url.to_dict(),
            'linkedin_url':      self.linkedin_url.to_dict(),
            'recent_news':       self.recent_news.to_dict(),
        }

    def to_meta_dict(self) -> dict:
        form_fields = self.to_form_dict()
        populated   = sum(1 for f in form_fields.values() if f.get('value'))
        return {
            'run_id':            self.agent_run_id,
            'total_searches':    self.total_searches,
            'total_urls_fetched':self.total_urls_fetched,
            'tokens_used':       self.tokens_used,
            'run_duration_sec':  round(self.run_duration_sec, 1),
            'fields_populated':  populated,
            'fields_total':      len(form_fields),
            'status':            self.status,
            'error_message':     self.error_message,
        }
