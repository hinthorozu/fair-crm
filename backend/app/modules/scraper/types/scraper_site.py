"""Reserved site keys for planned fair adapters."""

from enum import StrEnum


class ScraperSiteKey(StrEnum):
    TUYAP = "tuyap"
    TUYAP_OLD = "tuyap_old"
    TUYAP_NEW = "tuyap_new"
    CUSTOMER_CONTACT_ENRICHMENT = "customer_contact_enrichment"
    IFM = "ifm"
    HANNOVER = "hannover"
    CANTON = "canton"
    F_ISTANBUL = "f_istanbul"
    EXPOMED = "expomed"
    CNR = "cnr"
