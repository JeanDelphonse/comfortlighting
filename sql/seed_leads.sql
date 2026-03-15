-- Leads imported from docs/SalesStatusBlank.xlsx
-- Generated: 2026-03-09
--
-- Notes:
--   - action mapped to nearest ACTION_VALUE (app enum)
--   - contacts/numbers with multiple lines collapsed to single value
--   - missing required fields (contact, number, email) filled with N/A / unknown@unknown.com
--   - potential formula cells that resolved to 0 set to NULL
--   - run after schema.sql

INSERT INTO `leads` (`company_name`, `action`, `contact`, `address`, `number`, `email`, `notes`, `sq_ft`, `targets`, `potential`, `progress`, `expected`, `roi`, `annual_sales_locations`) VALUES
  ('6 STAR variety and party (6 star outlet) - 3054 Story Rd San Jose, CA 95127', 'Follow-Up', 'N/A', NULL, '(408) 729-0144', 'unknown@unknown.com', '96/100 lights-about $5700-$6k cost, Light reading:230, 2x light/half the power, Gave owner estimate/showed light&reading', NULL, '6', NULL, NULL, NULL, NULL, NULL),
  ('9 West', 'Follow-Up', 'N/A', NULL, 'N/A', 'unknown@unknown.com', '3 ct, 2 ft, 24 fix = 72 (green caps)', NULL, '2', NULL, NULL, NULL, NULL, NULL),
  ('ABM Pleasanton', 'Contacted', 'N/A', NULL, 'N/A', 'unknown@unknown.com', 'meeting w/ 4 ppl 7/18, IM will email', NULL, NULL, NULL, NULL, NULL, NULL, NULL),
  ('AC Foods Wholesale - Fleming business park', 'Follow-Up', 'N/A', NULL, 'N/A', 'unknown@unknown.com', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
  ('All Weather Architectural Aluminum', 'Contacted', 'Nick Codding - PM; Steve Trent; Kathy Hobbs - Purchasing Manager', '777 Aldridge Rd, Vacaville, CA', '707-452-1600', 'nicolas.codding@allweatheraa.com', NULL, 60000, NULL, NULL, NULL, NULL, NULL, NULL),
  ('All Weather Insulated Panels', 'Follow-Up', 'Jimmy Mcintire - Plant Manager; Mike Nelepovitz', '929 Aldridge Rd, Vacaville, CA', '707-359-2280 x307', 'mnelepovitz@awipanels.com', NULL, NULL, '50,000-80,000 sq ft', NULL, NULL, NULL, NULL, NULL),
  ('Alliance Residential / Encasa', 'New Lead', 'N/A', '111 West Saint John Street, Suite 445, San Jose, CA 95113', '408-769-4250', 'unknown@unknown.com', 'Lights will turn off and on for garage, saves a ton of $. Property management. 7 locations CA / ~25 nationally. 10/05/18: 8 CA locations, 35 nationwide', NULL, 'Garage lighting', NULL, NULL, NULL, NULL, '~35 nationwide locations'),
  ('Betts Manufacturing', 'Follow-Up', 'Steve Thatcher (Fresno)', '950 Doolittle Dr, San Leandro, CA 94577; 2867 S Maple Ave, Fresno, CA 93725', '(510) 633-4500', 'unknown@unknown.com', '4/6/16 3:30pm meeting. Carlos no longer there 03/30/18. Call Fresno - Steve Thatcher > call corp.', 20000, 'Meet: 6/28; Test install: 7/22; Final T&C: 8/16; PO: 8/30/16', 25000.00, NULL, NULL, NULL, NULL),
  ('Cheese Steak Shop', 'Contacted', 'Ron', NULL, '(408) 935-3161', 'unknown@unknown.com', 'IM picked up lights, Ron said too expensive. 02/21/19 - lights too expensive; suggested chamber website for ads; got his email.', NULL, NULL, NULL, NULL, NULL, NULL, NULL),
  ('Harbor Freight Tools', 'Follow-Up', 'Roger - Manager', NULL, '1-805-388-1000', 'unknown@unknown.com', '9/26 called, Roger said to call corporate. Multiple follow-up attempts for Mike Wallace - no contact made through 2/8.', NULL, NULL, NULL, NULL, NULL, NULL, NULL),
  ('Inprintz', 'Follow-Up', 'Dave Cheng', '924 Borregas Ave, Sunnyvale, CA 94089', '(408) 541-8500', 'unknown@unknown.com', '08/21/18 visit Dave - very impressive, long-standing business, has MH 400w, maintenance guy is Enriquez. 06/24/19 Dave remembered, took info for Enriquez.', NULL, NULL, NULL, NULL, NULL, NULL, NULL),
  ('Iron Mountain', 'Follow-Up', 'Oscar Montano - Operations Supervisor', '565 Sinclair Frontage Rd, Milpitas, CA 95035', '800-327-8345', 'unknown@unknown.com', '~100,000 sq ft. Visited 7/6, corporate makes decisions. CBRE handles maintenance. Oscar interested. Need to contact Debra Green - fac. mgr. 3 Iron Mountain locations.', NULL, 'Warehouse / facility lighting', NULL, NULL, NULL, NULL, '3 Iron Mountain locations'),
  ('J.Crew (Great Mall)', 'Follow-Up', 'N/A', NULL, 'N/A', 'unknown@unknown.com', '2 ct, 2 ft, 48 fixtures = 96 (thin, green caps)', NULL, '2 ct fixtures', NULL, NULL, NULL, NULL, NULL),
  ('J.B. Hunt Transport', 'New Lead', 'N/A', 'HQ: 615 JB Hunt Drive, Lowell, AR 72745', '1-800-452-4868', 'unknown@unknown.com', '11/19/19 ~15 locations. Sales contact = CrowCanyon.', NULL, NULL, NULL, NULL, NULL, NULL, '~15 locations'),
  ('John Deere', 'New Lead', 'Mike Puck', '17400 Shideler Pkwy Building 1, Lathrop, CA 95330', '(209) 923-6116', 'MikePuck@JohnDeere.com', '11/12/19 huge building. 11/13/19 emailed info.', NULL, NULL, NULL, NULL, NULL, NULL, NULL),
  ('Laser Impressions', 'Follow-Up', 'Amy', '1188 Elko Dr, Sunnyvale, CA 94089', '(408) 734-2012', 'unknown@unknown.com', '15,000 sq ft. Amy seemed put out at 7/13 visit. Email: 40w to 18w, $25/yr electric savings, $17 each, ROI 9 months.', 15000, 'All fixtures', 2.00, NULL, NULL, NULL, NULL),
  ('Pitco Foods', 'Follow-Up', 'Bill (SJ HQ) x1044', '567 Cinnabar St, San Jose, CA; 727 Kennedy St, Oakland, CA', '800-464-4441', 'barnenakis@pitcofoods.com', 'Multiple follow-up attempts 11/9 through 2/15. Bill has no direct extension; email provided 11/16.', NULL, NULL, NULL, NULL, NULL, NULL, '2 locations: San Jose, Oakland');
