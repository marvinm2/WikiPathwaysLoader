-- WikiPathways SPARQL endpoint — restore /.well-known/void.
--
-- REGRESSION, not a new feature. strato1 served this and still does: its ~/wikipathways.sh
-- downloads the VoID a second time under the extensionless name `void` (lines 189-192) and
-- copies it into the Snorql UI's document root (lines 386-398,
-- `cp void "$BASE_DIR_EP/snorql-extended/.well-known/"`), where the bind-mounted Apache served
-- it. The 2026-07-16 cluster port dropped both steps, and the cluster's Snorql UI runs from a
-- GHCR image with no bind mount at all (`docker service inspect
-- wikipathways_wikipathways-snorql` shows `Mounts: null`). So /.well-known/void 404'd here from
-- 16 July to 6 August. YummyData's `endpoint.void` check tries GET /.well-known/void first.
--
-- Restored by CONSTRUCTing the VoID back out of the store rather than by re-copying a file: the
-- VoID is already loaded monthly as part of WikiPathways.ttl, so this needs no loader change, no
-- bind mount and no container restart.
--
-- ---------------------------------------------------------------------------------------------
-- APPLY THIS TO **BOTH** ep AND ep2.
--
-- This endpoint is blue-green: switch-wikipathways.sh flips which instance Traefik's
-- `wikipathways-live` service points at. A rule applied to only one instance works until the
-- next cutover and then vanishes with no error anywhere. That — not the monthly reload — is the
-- durability constraint here.
--
-- The reload does NOT wipe this. Tested 2026-08-06 on a throwaway Virtuoso of the same image:
-- the VHOST row, the rewrite rule and the rule list all survive RDF_GLOBAL_RESET() (which is
-- load.sh's only destructive step) and a container restart. Rewrite rules and VHOSTs live in
-- ordinary SQL tables; RDF_GLOBAL_RESET() clears the quad store. Neither loader deletes the
-- database directory. Earlier cluster docs claimed the opposite; they were wrong and have been
-- corrected.
-- ---------------------------------------------------------------------------------------------
--
-- SELECTOR — deliberately five types, NOT the two the AOP-Wiki equivalent uses.
--
-- AOP-Wiki's rule filters on void:Dataset || void:Linkset. Copied here verbatim that returns
-- 152 of 178 triples, silently dropping the datasetDescription, all three dcat:Distribution
-- sub-datasets (rdf/wp, rdf/gpml, rdf/authors) and the Wikidata publisher node. The five types
-- below reproduce strato1's served document exactly — 178 triples, set-equal, verified against
-- ~/WikiPathways-EP/snorql-extended/.well-known/void at the same 20260710 release vintage.
--
-- Selecting on rdf:type rather than on a subject-URI prefix avoids hardcoding the publisher. The
-- prefix form needs an explicit Q131790020 term alongside the data.wikipathways.org prefix to reach
-- all 178 triples, because the publisher node is a Wikidata IRI; if that entity ever changed, the
-- rule would silently drop it. foaf:Organization picks it up generically, and is safe as an
-- unscoped selector: there is exactly one in the whole store.
--
-- CORRECTION: an earlier version of this comment justified the type selector by saying it keeps the
-- rule "independent of the release date embedded in every data.wikipathways.org subject". That is
-- wrong. The prefix that was actually tested is the bare `https://data.wikipathways.org/`, which
-- carries no date and would have survived reloads perfectly well. The hardcoded publisher above is
-- the real, and smaller, advantage. Both forms are release-date independent.
--
-- After the next monthly reload this will also pick up the ontology datasets added by
-- wikipathways/GPML2RDF PR #28, so the served document will stop being byte-equal to strato1's.
-- That is intended — it is a superset, and strato1 has no ontology VoID at all.
--
-- One rule, no accept_pattern, no format. Virtuoso's URR_ACCEPT_PATTERN does not behave as
-- OpenLink documents it (a rule gated on Accept never fires; application/rdf+xml 406s whether
-- the plus is spelled `.` as their own example writes it, or `[+]`). Without a gate Virtuoso
-- negotiates every type correctly and returns Turtle for */*, so the gate bought nothing.
--
-- target_compose is an sprintf format string, hence the doubled %.
--
-- Revert:
--   DB.DBA.VHOST_REMOVE (lpath=>'/void-full');
--   DELETE FROM DB.DBA.URL_REWRITE_RULE_LIST WHERE URRL_LIST = 'wp_void_rule_list1';
--   DELETE FROM DB.DBA.URL_REWRITE_RULE WHERE URR_RULE LIKE 'wp_void_rule%';

DELETE FROM DB.DBA.URL_REWRITE_RULE_LIST WHERE URRL_LIST = 'wp_void_rule_list1';
DELETE FROM DB.DBA.URL_REWRITE_RULE WHERE URR_RULE LIKE 'wp_void_rule%';

DB.DBA.URLREWRITE_CREATE_REGEX_RULE (
    'wp_void_rule1',
    1,
    '/void-full',
    vector (),
    0,
    '/sparql?query=CONSTRUCT%%20%%7B%%20%%3Fs%%20%%3Fp%%20%%3Fo%%20%%7D%%20WHERE%%20%%7B%%20GRAPH%%20%%3Chttp%%3A%%2F%%2Frdf.wikipathways.org%%2F%%3E%%20%%7B%%20%%3Fs%%20a%%20%%3Ft%%20.%%20%%3Fs%%20%%3Fp%%20%%3Fo%%20.%%20FILTER%%28%%3Ft%%20IN%%20%%28%%3Chttp%%3A%%2F%%2Frdfs.org%%2Fns%%2Fvoid%%23Dataset%%3E%%2C%%3Chttp%%3A%%2F%%2Frdfs.org%%2Fns%%2Fvoid%%23Linkset%%3E%%2C%%3Chttp%%3A%%2F%%2Frdfs.org%%2Fns%%2Fvoid%%23DatasetDescription%%3E%%2C%%3Chttp%%3A%%2F%%2Fwww.w3.org%%2Fns%%2Fdcat%%23Distribution%%3E%%2C%%3Chttp%%3A%%2F%%2Fxmlns.com%%2Ffoaf%%2F0.1%%2FOrganization%%3E%%29%%29%%20%%7D%%20%%7D',
    vector (),
    null,
    null,
    2,
    null
);

DB.DBA.URLREWRITE_CREATE_RULELIST (
    'wp_void_rule_list1',
    1,
    vector ('wp_void_rule1')
);

DB.DBA.VHOST_REMOVE (lpath=>'/void-full');

DB.DBA.VHOST_DEFINE (
    lpath=>'/void-full',
    ppath=>'/DAV/',
    is_dav=>1,
    vsp_user=>'dba',
    opts=>vector ('url_rewrite', 'wp_void_rule_list1')
);

checkpoint;

SELECT HP_LPATH FROM DB.DBA.HTTP_PATH WHERE HP_LPATH = '/void-full';
SELECT URR_RULE FROM DB.DBA.URL_REWRITE_RULE WHERE URR_RULE LIKE 'wp_void_rule%';
