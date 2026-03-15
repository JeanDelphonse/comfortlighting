-- ComfortLighting Contract Clause Templates Seed
-- Run AFTER schema.sql
-- These templates use {{PLACEHOLDER}} tokens substituted by the AI during contract generation.

INSERT INTO `clause_templates` (`clause_key`, `clause_text`, `version`, `active`) VALUES

('PARTIES_TEMPLATE',
'This LED Lighting Services Agreement (the "Agreement") is entered into as of {{EFFECTIVE_DATE}}, by and between ComfortLighting.net LLC, a California limited liability company with its principal place of business at 123 Bright Way, San Jose, CA 95110 ("Service Provider"), and {{COMPANY_NAME}}, located at {{CLIENT_ADDRESS}} ("Client"). The authorized representative of Client for purposes of this Agreement is {{CONTACT_NAME}} ({{CLIENT_EMAIL}}).',
1, 1),

('RECITALS_TEMPLATE',
'WHEREAS, Client operates a commercial facility of approximately {{SQ_FT}} square feet located at {{CLIENT_ADDRESS}} and desires to upgrade its lighting infrastructure to energy-efficient LED technology; and WHEREAS, Service Provider has the expertise, licenses, and equipment to design, supply, and install commercial LED lighting systems; NOW THEREFORE, in consideration of the mutual covenants and agreements set forth herein, the parties agree as follows.',
1, 1),

('SCOPE_OF_WORK_TEMPLATE',
'Service Provider shall design, procure, and install LED lighting fixtures throughout the Client\'s facility totaling approximately {{SQ_FT}} square feet, covering {{TARGET_ZONES}}. Service Provider shall manage all permitting, installation labor, and disposal of legacy fixtures in compliance with applicable regulations. A detailed project specification shall be agreed upon by both parties prior to commencement.',
1, 1),

('COMPENSATION_TEMPLATE',
'Client agrees to pay Service Provider the total contract amount of [TO BE CONFIRMED] (the "Contract Price") in accordance with the following schedule: [TO BE CONFIRMED]% upon contract execution; [TO BE CONFIRMED]% upon substantial completion. Payment is due within 30 days of invoice. Late payments shall accrue interest at 1.5% per month.',
1, 1),

('TIMELINE_TEMPLATE',
'Work shall commence on approximately {{START_DATE}} or such other date as mutually agreed in writing. Estimated completion is [TO BE CONFIRMED] weeks from commencement. Service Provider shall not be liable for delays caused by Client, supply chain disruptions, or force majeure events beyond Service Provider\'s reasonable control.',
1, 1),

('WARRANTY_TEMPLATE',
'Service Provider warrants all installed LED fixtures and components against defects in materials and workmanship for a period of ten (10) years from the date of substantial completion. Workmanship is warranted for two (2) years. Warranty claims must be submitted in writing within the applicable warranty period. This warranty does not cover damage caused by misuse, unauthorized modification, or acts of God.',
1, 1),

('PERFORMANCE_GUARANTEE_TEMPLATE',
'Service Provider guarantees that the installed lighting system shall achieve a minimum {{ROI_PERCENT}}% reduction in lighting energy consumption compared to the pre-installation baseline measurement. Energy consumption shall be measured over the 90-day period following substantial completion. If the guaranteed reduction is not achieved within 12 months, Service Provider shall provide remedial upgrades at no additional cost to Client.',
1, 1),

('INDEMNIFICATION_TEMPLATE',
'Each party (the "Indemnifying Party") shall indemnify, defend, and hold harmless the other party and its officers, directors, employees, and agents from and against any and all claims, damages, losses, costs, and expenses (including reasonable attorneys\' fees) arising out of or resulting from the Indemnifying Party\'s negligence, willful misconduct, or material breach of this Agreement.',
1, 1),

('LIMITATION_OF_LIABILITY_TEMPLATE',
'IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOSS OF PROFITS OR BUSINESS INTERRUPTION, REGARDLESS OF THE THEORY OF LIABILITY. SERVICE PROVIDER\'S TOTAL CUMULATIVE LIABILITY SHALL NOT EXCEED THE TOTAL CONTRACT PRICE PAID BY CLIENT UNDER THIS AGREEMENT IN THE TWELVE MONTHS PRECEDING THE CLAIM.',
1, 1),

('TERMINATION_TEMPLATE',
'Either party may terminate this Agreement for material breach upon thirty (30) days written notice if the breaching party fails to cure such breach within the notice period. Client may terminate for convenience upon sixty (60) days written notice; in such event, Client shall pay Service Provider for all work completed and non-cancellable commitments incurred prior to the termination date.',
1, 1),

('DISPUTE_RESOLUTION_TEMPLATE',
'The parties shall attempt in good faith to resolve any dispute through direct negotiation. If unresolved within 30 days, the dispute shall be submitted to non-binding mediation. If mediation fails, the dispute shall be resolved by binding arbitration under the Commercial Arbitration Rules of the American Arbitration Association. Each party waives the right to participate in any class action proceeding.',
1, 1),

('GOVERNING_LAW_TEMPLATE',
'This Agreement shall be governed by and construed in accordance with the laws of the State of California, without regard to its conflict of law principles. Any legal action arising under this Agreement shall be brought exclusively in the state or federal courts located in Santa Clara County, California, and each party consents to personal jurisdiction therein.',
1, 1),

('NOTICES_TEMPLATE',
'All notices required or permitted under this Agreement shall be in writing and delivered by email (with confirmation of receipt) and certified mail to the addresses set forth in Section 1 (Parties). Notices shall be effective upon the earlier of confirmed email receipt or three business days after mailing. Notice address for Client: {{CONTACT_NAME}}, {{CLIENT_EMAIL}}, {{CLIENT_ADDRESS}}. Notice address for Service Provider: ComfortLighting.net LLC, 123 Bright Way, San Jose, CA 95110.',
1, 1),

('ENTIRE_AGREEMENT_TEMPLATE',
'This Agreement constitutes the entire agreement between the parties with respect to its subject matter and supersedes all prior proposals, representations, discussions, negotiations, and understandings, whether oral or written. This Agreement may not be amended except by a written instrument signed by authorized representatives of both parties. If any provision of this Agreement is found to be unenforceable, the remaining provisions shall remain in full force and effect.',
1, 1),

('SIGNATURE_BLOCK_TEMPLATE',
'IN WITNESS WHEREOF, the parties have executed this LED Lighting Services Agreement as of the date first written above. Each signatory represents that they are duly authorized to execute this Agreement on behalf of the respective party.',
1, 1);
