/* Traducerea în engleză a paginilor fără sistem propriu de limbă:
   registrele de acorduri (Monitorul Oficial și legis.md), HG 246 și „Despre".

   Paginile se desenează în română, din date în română. Cu engleza aleasă,
   scriptul înlocuiește textele interfeței — titluri, butoane, etichete,
   explicații — după un dicționar de fraze exacte și câteva tipare cu numere.
   Denumirile oficiale ale actelor și ale acordurilor rămân în română: sunt
   citate din Monitorul Oficial și din legis.md, iar o traducere automată a lor
   ar fi o sursă falsă. Ce se redesenează ulterior (filtre, rânduri deschise)
   e prins de un MutationObserver.

   Limba aleasă e ținută în localStorage (cheia „limba") și în ?lang=en, ca un
   link în engleză să se deschidă în engleză. Blocurile scrise direct în ambele
   limbi poartă data-bloc="ro" / data-bloc="en" și se ascund unul pe altul. */
(function () {
  'use strict';

  var EXACT = {
    // antet, indicatori
    'Acorduri de asistență externă': 'External assistance agreements',
    'Acorduri de asistență externă · Registrul de stat': 'External assistance agreements · State Register',
    'Un acord, un rând. Actele publicate în Monitorul Oficial sunt grupate pe acordul din care fac parte, cu etapa la care a ajuns fiecare.':
      'One agreement, one row. The acts published in the Official Gazette are grouped by the agreement they belong to, with the stage each agreement has reached.',
    'Versiune de test': 'Test version',
    ': actele sunt găsite prin căutare în titlu și filtrate automat, deci pot exista și acte în plus, și acte scăpate.':
      ': acts are found by searching their titles and filtered automatically, so some extra or missing acts are possible.',
    'Acoperă:': 'Covers:', 'Ultima verificare:': 'Last check:', 'Ediții parcurse:': 'Editions read:', 'Extras la:': 'Extracted on:', 'Sursa:': 'Source:',
    'Acorduri': 'Agreements', 'Creditori': 'Creditors', 'Ratificate sau aprobate': 'Ratified or approved', 'Cu dată de intrare în vigoare': 'With an entry-into-force date',
    'din legea de ratificare sau din ordin': 'from the ratification law or the order',
    // panoul etapelor
    'Cum se încheie un acord': 'How an agreement is concluded',
    'Etapele': 'Stages', 'Tipuri de finanțare': 'Types of financing', 'Contracte de stat': 'State contracts',
    'Apasă o etapă pentru detalii': 'Click a stage for details', 'Apasă din nou ca să închizi': 'Click again to close',
    'Inițiere negocieri': 'Start of negotiations', 'Aprobare semnare': 'Approval to sign', 'Aprobare proiect de lege': 'Approval of the draft law',
    'Ratificare sau aprobare': 'Ratification or approval', 'Decret de promulgare': 'Promulgation decree',
    'Proiect de lege': 'Draft law', 'Ordin de punere în aplicare': 'Implementing order',
    'Guvern sau Președinte': 'Government or President', 'Guvern': 'Government', 'Parlament sau Guvern': 'Parliament or Government', 'Președinte': 'President',
    'Ce act apare în Monitor': 'Which act appears in the Gazette', 'Cine emite actul': 'Who issues the act',
    'Ultimele acte din această etapă': 'Latest acts at this stage',
    'Hotărâre de Guvern, ori decret prezidențial la tratatele interstatale': 'Government decision, or presidential decree for inter-state treaties',
    'Etape obligatorii care nu produc niciun act publicat în Monitor': 'Mandatory stages that produce no act published in the Gazette',
    'Consultări prealabile și examinarea oportunității': 'Preliminary consultations and assessment of the opportunity',
    'Rundele de negociere și rapoartele acestora': 'Negotiation rounds and their reports',
    'Avizarea de către ministere și avizul Comisiei politică externă': 'Endorsement by ministries and by the foreign policy committee',
    'Parafarea textului': 'Initialling of the text', 'Eliberarea deplinelor puteri': 'Issuing full powers', 'Semnarea propriu-zisă': 'The signing itself',
    'Instrumentul de ratificare și schimbul instrumentelor': 'Instrument of ratification and exchange of instruments',
    'Intrarea în vigoare a acordului însuși — se produce la schimbul instrumentelor, iar ordinul MAE care o anunță e colectiv și nu numește acordul':
      'Entry into force of the agreement itself — happens at the exchange of instruments; the Foreign Ministry order announcing it is collective and does not name the agreement',
    'Legea de ratificare a intrat în vigoare la publicarea în Monitor. Acordul intră în vigoare separat, după schimbul instrumentelor.':
      'The ratification law entered into force on publication in the Gazette. The agreement itself enters into force separately, after the exchange of instruments.',
    'Acord interinstituțional: autoritatea responsabilă a publicat ordinul care anunță data intrării în vigoare (HG 377/2018, anexa 1¹, pct. 44).':
      'Inter-institutional agreement: the responsible authority published the order announcing the entry-into-force date (Government Decision 377/2018, annex 1¹, item 44).',
    // tipuri de finanțare
    'Regulamentul nu clasifică finanțările în cinci feluri, cum ar putea sugera etichetele de pe rânduri. Împarte':
      'The regulation does not sort financing into five kinds, as the row labels might suggest. It divides',
    'asistența externă': 'external assistance',
    'în financiară și tehnică, iar nerambursabilitatea e o însușire care poate însoți oricare dintre ele. Iată clasificarea, cu trimiterile exacte.':
      'into financial and technical, and being non-reimbursable is a property that can accompany either. Here is the classification, with exact references.',
    'Asistență externă': 'External assistance', 'Asistență externă nerambursabilă': 'Non-reimbursable external assistance',
    'Asistență financiară': 'Financial assistance', 'Asistență tehnică': 'Technical assistance', 'Suport bugetar': 'Budget support',
    'Asistență financiară nerambursabilă (pct. 9.20)': 'Non-reimbursable financial assistance (item 9.20)',
    'Asistență financiară rambursabilă (pct. 9.20)': 'Reimbursable financial assistance (item 9.20)',
    'Consultanță, instruire, expertiză (pct. 9.21)': 'Consultancy, training, expertise (item 9.21)',
    'Categoria-părinte (pct. 9.20)': 'Parent category (item 9.20)', 'Marcaj, nu categorie (pct. 9.20¹)': 'A marker, not a category (item 9.20¹)',
    'Noțiunea-umbrelă: asistență financiară și tehnică acordată Republicii Moldova, Guvernului sau altor autorități publice de comunitatea partenerilor externi de dezvoltare.':
      'The umbrella notion: financial and technical assistance provided to the Republic of Moldova, the Government or other public authorities by the community of external development partners.',
    'Însușire transversală, nu o categorie aparte: asistență financiară SAU tehnică acordată cu titlu gratuit, la nivel de stat, guvernamental ori interinstituțional.':
      'A cross-cutting property, not a separate category: financial OR technical assistance provided free of charge, at state, government or inter-institutional level.',
    'Suport financiar acordat sub formă de împrumuturi și/sau granturi, pentru implementarea proiectelor și programelor.':
      'Financial support in the form of loans and/or grants, for implementing projects and programmes.',
    'Asistență financiară externă nerambursabilă, transmisă de partenerul extern de dezvoltare beneficiarului sau implementatorului pentru realizarea unor proiecte ori programe.':
      'Non-reimbursable external financial assistance, passed by the external development partner to the beneficiary or implementer to carry out projects or programmes.',
    'Formă rambursabilă a asistenței financiare. Contractele de împrumut de stat extern nu urmează procedura contractelor de stat, ci Legea nr. 419/2006 privind datoria sectorului public, garanțiile de stat și recreditarea de stat.':
      'A reimbursable form of financial assistance. External state loan contracts do not follow the state-contract procedure but Law no. 419/2006 on public sector debt, state guarantees and state on-lending.',
    'Sprijin nerambursabil pentru transfer de cunoștințe, expertiză și tehnologii — consultanță, instruire, studii, schimb de experiență — inclusiv dotarea cu echipamente și materiale.':
      'Non-reimbursable support for the transfer of knowledge, expertise and technology — consultancy, training, studies, exchange of experience — including equipment and materials.',
    'Asistență financiară de la Uniunea Europeană, instituțiile financiare internaționale sau guvernele altor state, transferată direct într-un buget component al bugetului public național, pentru a susține reformele agreate. Grupul de negociere este condus de Ministerul Finanțelor.':
      'Financial assistance from the European Union, international financial institutions or other governments, transferred directly into a component of the national public budget to support agreed reforms. The negotiating group is led by the Ministry of Finance.',
    'Însoțește categoria, nu o înlocuiește. Suportul bugetar descrie unde ajung banii — direct într-un buget component al bugetului public național — nu dacă se întorc. Contractul de performanță pentru reforma sectorială al Uniunii Europene e un grant cu acest marcaj; Facilitatea de reformă și creștere e un împrumut cu același marcaj. Ca și categorie separată, ascundea tocmai ce contează: dacă statul are de rambursat.':
      'It accompanies the category, it does not replace it. Budget support describes where the money goes — directly into a component of the national public budget — not whether it is repaid. The EU sector reform performance contract is a grant with this marker; the Reform and Growth Facility is a loan with the same marker. As a separate category it hid exactly what matters: whether the state has to repay.',
    'Regulamentul le enumeră alături de împrumuturi și granturi, printre formele prin care un partener extern de dezvoltare acordă sprijin.':
      'The regulation lists them alongside loans and grants among the ways an external development partner provides support.',
    'Garanții și alte instrumente de sprijin': 'Guarantees and other support instruments', 'Cofinanțare': 'Co-financing',
    'Contribuția părții moldovenești — financiară sau nefinanciară, prin servicii și expertiză tehnică — la realizarea unui proiect împreună cu alți parteneri.':
      'The Moldovan side\'s contribution — financial or in kind, through services and technical expertise — to a project carried out with other partners.',
    'Cum ajunge un act într-o categorie': 'How an act ends up in a category',
    'Categoriile de pe rânduri sunt chiar cele de mai sus. Titlurile actelor nu folosesc însă mereu cuvintele din lege, așa că iată regula după care fiecare titlu ajunge la o categorie. Apasă una ca să filtrezi registrul.':
      'The row categories are the ones above. Act titles do not always use the legal wording, so here is the rule by which each title is assigned a category. Click one to filter the register.',
    'Prinde „acord de împrumut", dar și denumirile comerciale ale aceluiași lucru: facilitate sau linie de credit, ori contractul de finanțare al Băncii Europene de Investiții. Niciuna nu e o categorie legală separată.':
      'Catches "loan agreement", and also the commercial names for the same thing: facility or credit line, or the European Investment Bank\'s finance contract. None of them is a separate legal category.',
    'Se folosește doar când titlul spune „acord de finanțare" fără să arate dacă banii se întorc, iar finanțatorul nu e nici bancă de dezvoltare, nici agenție de donații. În rest, decide finanțatorul: acordul de finanțare cu AID e împrumut, iar cele cu Comisia Europeană sau cu Crucea Roșie sunt granturi.':
      'Used only when the title says "financing agreement" without showing whether the money is repaid, and the funder is neither a development bank nor a donor agency. Otherwise the funder decides: a financing agreement with IDA is a loan, those with the European Commission or the Red Cross are grants.',
    'Asistența tehnică ajunge în Monitor pe altă cale.': 'Technical assistance reaches the Gazette by another route.',
    'Contractele de stat fără impact bugetar care privesc proiecte de asistență tehnică se semnează direct de conducătorul autorității, fără avizare și fără hotărâre de Guvern — anexa nr. 1¹, pct. 6. Dar nu rămân nepublicate: toate contractele de stat se publică în Monitor, iar autoritatea care semnează emite un ordin cu data intrării în vigoare, publicat în 10 zile împreună cu textul contractului — pct. 40 și 44. Așa apar acordurile de asistență tehnică încheiate de ministere cu PAM, GIZ sau Agenția Elvețiană pentru Dezvoltare și Cooperare: nu ca lege sau hotărâre, ci ca ordin al ministerului semnatar.':
      'State contracts with no budget impact that concern technical assistance projects are signed directly by the head of the authority, without endorsement and without a Government decision — annex 1¹, item 6. They are still published: every state contract is published in the Gazette, and the signing authority issues an order with the entry-into-force date, published within 10 days together with the contract text — items 40 and 44. That is how technical assistance agreements signed by ministries with WFP, GIZ or the Swiss Agency for Development and Cooperation appear: not as a law or decision, but as an order of the signing ministry.',
    // contracte de stat
    'O parte din acordurile de aici nu sunt tratate internaționale, ci': 'Some of the agreements here are not international treaties but',
    'contracte de stat': 'state contracts',
    'Cu impact financiar asupra bugetului de stat': 'With a financial impact on the state budget', 'Cu impact asupra bugetului autorității': 'With an impact on the authority\'s budget',
    'Fără impact bugetar': 'No budget impact', 'De colaborare interinstituțională': 'Inter-institutional cooperation',
    'Implică angajamente care cer alocări suplimentare din bugetul de stat.': 'Involves commitments that require additional allocations from the state budget.',
    'Angajamentele se acoperă din mijloacele deja aprobate în bugetul autorității.': 'Commitments are covered from funds already approved in the authority\'s budget.',
    'Nu cere alocarea de resurse din bugetul de stat.': 'Requires no allocation from the state budget.',
    'Nu conține prevederi despre asistență externă și nu implică angajamente financiare suplimentare.': 'Contains no provisions on external assistance and involves no additional financial commitments.',
    'Traseul până la intrarea în vigoare': 'Route to entry into force',
    'Semnat direct de conducătorul autorității, fără procedura de avizare.': 'Signed directly by the head of the authority, without the endorsement procedure.',
    'Se semnează direct de conducătorul autorității, fără avizare și fără hotărâre de Guvern. Intră în vigoare la semnare. În Monitor apare doar ordinul care anunță data intrării în vigoare, publicat în 10 zile împreună cu textul contractului.':
      'Signed directly by the head of the authority, without endorsement and without a Government decision. Enters into force on signature. Only the order announcing the entry-into-force date appears in the Gazette, published within 10 days together with the contract text.',
    'Contractele de stat fără impact bugetar, semnate direct': 'State contracts with no budget impact, signed directly',
    // analiza
    'Cum merg acordurile': 'How agreements progress', 'Pâlnia etapelor': 'Stage funnel', 'Cât durează': 'How long it takes', 'Pe ani': 'By year',
    'Inițierea negocierilor': 'Start of negotiations', 'Aprobarea semnării': 'Approval to sign', 'Proiectul de lege': 'Draft law',
    'Ratificare / aprobare': 'Ratification / approval', 'Promulgare': 'Promulgation',
    'Din': 'Of', 'mediana': 'the median', ', durata tipică.': ', the typical duration.',
    'Zilele dintre datele edițiilor în care au apărut actele succesive ale aceluiași acord. Bara arată intervalul în care se încadrează jumătate din acorduri (de la sfertul cel mai rapid la cel mai lent), iar linia din ea —':
      'Days between the editions in which successive acts of the same agreement appeared. The bar shows the range covering half of the agreements (from the fastest quarter to the slowest), and the line inside it —',
    'Inițiere → aprobarea semnării': 'Start → approval to sign', 'Semnare → proiectul de lege': 'Signature → draft law',
    'Proiectul de lege → ratificare': 'Draft law → ratification', 'Ratificare → promulgare': 'Ratification → promulgation',
    'Semnare → ratificare (total)': 'Signature → ratification (total)', 'Inițiere → ratificare (total)': 'Start → ratification (total)',
    'Semnare → ratificare, după tipul acordului': 'Signature → ratification, by type of agreement',
    'prea puține date': 'too little data',
    'Acorduri noi pe an — anul primului act publicat al fiecărui acord — după tipul lui.': 'New agreements per year — the year of each agreement\'s first published act — by type.',
    'Acorduri noi pe ani, după tip': 'New agreements per year, by type',
    'Arată ca tabel': 'Show as table', 'Altele': 'Other', 'An': 'Year', 'Total': 'Total',
    // listă, filtre
    'Acte': 'Acts', 'Caută…': 'Search…', 'Caută': 'Search', 'Caută (ex. BERD, Europeană, Japonia)…': 'Search (e.g. EBRD, European, Japan)…',
    'Partener': 'Partner', 'Toți': 'All', 'Toți anii': 'All years', 'Tip': 'Type', 'Toate': 'All', 'Gata': 'Done',
    'Ultimul an': 'Last year', 'nimic bifat = toți': 'nothing ticked = all', 'Șterge filtrul': 'Clear filter',
    'Șterge filtrul Partener': 'Clear the Partner filter', 'Șterge filtrul An': 'Clear the Year filter',
    'Acordul': 'Agreement', 'Categorie': 'Category', 'Etape parcurse': 'Stages completed', 'Semnat': 'Signed',
    'Act': 'Act', 'Etapa': 'Stage', 'Denumire': 'Title', 'Ediția': 'Edition',
    'Negocieri': 'Negotiation', 'Semnare': 'Signature', 'Ratificare': 'Ratification',
    'Grant': 'Grant', 'Împrumut': 'Loan', 'suport bugetar': 'budget support',
    '· legea de ratificare': '· ratification law', '· ordin de punere în aplicare': '· implementing order',
    'Descarcă exact rândurile filtrate': 'Download exactly the filtered rows',
    'Deschide actul în Registrul de stat (legis.md)': 'Open the act in the State Register (legis.md)',
    'Copiază linkul acestui acord': 'Copy the link to this agreement', 'Linkul a fost copiat': 'Link copied',
    '↑ Începutul paginii': '↑ Top of the page', '← Donatori și proiecte': '← Donors & projects', 'Despre date': 'About the data',
    'Acorduri · Monitorul Oficial': 'Agreements · Official Gazette', 'Acorduri · legis.md': 'Agreements · legis.md',
    'Niciun acord': 'No agreements', 'Nimic nu corespunde filtrelor.': 'Nothing matches the filters.',
    'Nimic găsit.': 'Nothing found.', 'Se încarcă': 'Loading', 'Preiau registrul.': 'Fetching the register.',
    // parteneri: denumiri generice
    'Bancă comercială străină': 'Foreign commercial bank', 'Regatul Unit': 'United Kingdom', 'Elveția': 'Switzerland', 'Franța': 'France', 'România': 'Romania',
    'Banca Mondială': 'World Bank', 'Consiliul Europei': 'Council of Europe', 'Fondul Global': 'Global Fund',
    'Uniunea Europeană, Comisia Europeană': 'European Union, European Commission',
    'Asociația Internațională pentru Dezvoltare (Banca Mondială) IDA': 'International Development Association (World Bank) IDA',
    'Banca Internațională pentru Reconstrucție și Dezvoltare (Banca Mondială) IBRD': 'International Bank for Reconstruction and Development (World Bank) IBRD',
    'Banca Europeană pentru Reconstrucție și Dezvoltare EBRD': 'European Bank for Reconstruction and Development EBRD',
    'Banca Europeană de Investiții EIB': 'European Investment Bank EIB', 'Banca de Dezvoltare a Consiliului Europei': 'Council of Europe Development Bank',
    'Agenția Franceză de Dezvoltare, Franța': 'French Development Agency, France', 'Agenția Japoneză de Cooperare Internațională, Japonia': 'Japan International Cooperation Agency, Japan',
    'Agenția de Cooperare Internațională a Germaniei': 'German Agency for International Cooperation', 'Banca Germană de Dezvoltare, Germania': 'German Development Bank, Germany',
    'Banca Export-Import a Japoniei': 'Export-Import Bank of Japan', 'Corporația Financiară Internațională': 'International Finance Corporation',
    'Corporația Provocările Mileniului, Statele Unite': 'Millennium Challenge Corporation, United States', 'Statele Unite ale Americii, USAID': 'United States of America, USAID',
    'Programul Națiunilor Unite pentru Dezvoltare UNDP': 'United Nations Development Programme UNDP', 'Programul Alimentar Mondial WFP': 'World Food Programme WFP',
    'Fondul Internațional pentru Dezvoltare Agricolă IFAD': 'International Fund for Agricultural Development IFAD',
    'Federația Internațională a Societăților de Cruce Roșie și Semilună Roșie': 'International Federation of Red Cross and Red Crescent Societies',
    'Danemarca, Norvegia, Fondul Nordic de Dezvoltare, NEFCO': 'Denmark, Norway, Nordic Development Fund, NEFCO',
    // HG 246
    'HG 246 — proiecte expirate': 'HG 246 — expired projects', 'HG 246': 'HG 246',
    'Încarcă anexa nr. 1 la Hotărârea Guvernului nr. 246/2010. Fiecare proiect din listă e căutat după numărul de înregistrare în Platforma pentru gestionarea asistenței externe, iar cele a căror dată de finalizare a trecut sunt extrase într-un document Word cu aceeași structură, plus o coloană nouă cu data de finalizare.':
      'Upload annex no. 1 to Government Decision no. 246/2010. Each project in the list is looked up by its registration number in the Aid Management Platform, and those whose end date has passed are extracted into a Word document with the same structure, plus a new column with the end date.',
    '1. Documentul de comparat': '1. Document to compare',
    'Trage aici anexa în format Word, sau apasă ca s-o alegi': 'Drop the annex here in Word format, or click to choose it',
    'Fișier .docx — lista proiectelor de asistență tehnică în derulare': '.docx file — the list of ongoing technical assistance projects',
    'Se încarcă baza de proiecte…': 'Loading the project database…', 'Se citește documentul…': 'Reading the document…',
    'Comparația se face după numărul de înregistrare din coloana a doua a anexei, care este identificatorul proiectului în Platforma pentru gestionarea asistenței externe. Se caută în două surse: raportul live al platformei și arhiva încorporată, care acoperă perioada 1993–2022. Când proiectul apare în amândouă, câștigă datele live. Un proiect e considerat expirat dacă data lui de finalizare a trecut; proiectele fără dată de finalizare în platformă nu sunt incluse, fiindcă absența datei nu înseamnă că proiectul s-a încheiat.':
      'The comparison uses the registration number in the annex\'s second column, which is the project identifier in the Aid Management Platform. Two sources are searched: the platform\'s live report and the built-in archive covering 1993–2022. When a project is in both, the live data wins. A project counts as expired if its end date has passed; projects without an end date in the platform are left out, because a missing date does not mean the project has ended.',
    'Proiecte expirate în perioada aleasă': 'Projects expired in the chosen period', 'Niciun proiect expirat în perioada aleasă.': 'No project expired in the chosen period.',
    'Descarcă documentul Word': 'Download the Word document', 'Nr. de înregistrare': 'Registration no.', 'Denumirea proiectului': 'Project title',
    'Finanțator': 'Funder', 'Data de finalizare': 'End date', 'Sursa': 'Source', 'efectivă': 'actual', 'planificată': 'planned', 'arhivă': 'archive',
    'Proiecte în anexă': 'Projects in the annex', 'Negăsite în platformă': 'Not found in the platform', 'Fără dată de finalizare': 'No end date', 'Expirate, în perioadă': 'Expired, in the period',
    'Lăsând ambele câmpuri goale, intră toate.': 'Leaving both fields empty includes all.',
    'Alege un fișier .docx. Formatul vechi .doc trebuie salvat întâi ca .docx.': 'Choose a .docx file. The old .doc format must first be saved as .docx.',
    'Baza de proiecte nu s-a încărcat încă. Așteaptă câteva secunde.': 'The project database has not loaded yet. Wait a few seconds.',
    'numărul nu există în AMP': 'the number does not exist in AMP', 'nici efectivă, nici planificată': 'neither actual nor planned', 'fără dată efectivă în platformă': 'no actual date in the platform',
    'Arhivă:': 'Archive:', 'Acte publicate': 'Published acts', 'Elveția / Austria': 'Switzerland / Austria',
    'Hotărâre de Guvern pentru aprobarea semnării, apoi hotărâre de Guvern de aprobare a contractului. Intră în vigoare după aprobarea Guvernului.':
      'Government decision approving the signature, then a Government decision approving the contract. Enters into force after the Government approves it.',
    'Hotărâre de Guvern pentru aprobarea semnării, apoi lege de ratificare a Parlamentului. Intră în vigoare la data ultimei notificări dintre părți.':
      'Government decision approving the signature, then a ratification law passed by Parliament. Enters into force on the date of the last notification between the parties.',
    '„Acord de grant", grant investițional, asistență financiară nerambursabilă. Un grant care plătește servicii de consultanță rămâne grant: contează instrumentul.':
      '"Grant agreement", investment grant, non-reimbursable financial assistance. A grant that pays for consultancy is still a grant: the instrument is what counts.',
    'Acord sau contract de asistență ori cooperare tehnică, memorandum privind consultanța sau instruirea. Tot aici intră acordurile de colaborare prin care o agenție de dezvoltare implementează un proiect: aduc expertiză și capacitate de execuție, nu bani rambursabili. Ajung în Monitor prin ordinul autorității semnatare.':
      'Technical assistance or cooperation agreement or contract, memorandum on consultancy or training. Also cooperation agreements through which a development agency implements a project: they bring expertise and delivery capacity, not reimbursable money. They reach the Gazette through the signing authority\'s order.',
    ': acorduri care nu se supun dreptului internațional public sau care prevăd chiar în text că nu constituie tratat. Ele urmează un traseu propriu, stabilit de anexa nr. 1¹ la HG 377/2018, iar categoria contractului decide cine îl aprobă și când intră în vigoare. Banca Națională a Moldovei aplică proceduri proprii, iar contractele fără impact financiar pot fi încheiate prin schimb de scrisori.':
      ': agreements not governed by public international law, or that state in their text that they are not a treaty. They follow their own route, set by annex no. 1¹ to Government Decision 377/2018, and the contract category decides who approves it and when it enters into force. The National Bank of Moldova applies its own procedures, and contracts with no financial impact may be concluded by exchange of letters.',
    // meniu (index are propriul sistem)
    'Toate raioanele': 'All districts',
    'Despre date și metodologie': 'About the data and methodology'
  };

  // fraze cu numere și date
  var DATA = '(\\d{2}\\.\\d{2}\\.\\d{4})';
  var ETAPA = {'Inițiere negocieri':'Start of negotiations','Aprobare semnare':'Approval to sign','Aprobare proiect de lege':'Approval of the draft law',
    'Ratificare sau aprobare':'Ratification or approval','Decret de promulgare':'Promulgation decree','Inițierea negocierilor':'Start of negotiations',
    'Aprobarea semnării':'Approval to sign','Proiectul de lege':'Draft law','Ratificare / aprobare':'Ratification / approval','Promulgare':'Promulgation'};
  function durata(x){ return x.replace(/(\d+(?:,\d+)?) zile/g, '$1 days').replace(/(\d+(?:,\d+)?) luni/g, '$1 months').replace(/(\d+(?:,\d+)?) ani/g, '$1 years'); }
  var TIPARE = [
    [/^(\d+) acorduri$/, '$1 agreements'],
    [/^(\d+) acorduri · (\d+) acte$/, '$1 agreements · $2 acts'],
    [new RegExp('^(\\d+) act · ultimul: ' + DATA + '$'), '$1 act · latest: $2'],
    [new RegExp('^(\\d+) acte · ultimul: ' + DATA + '$'), '$1 acts · latest: $2'],
    [/^· (\d+) acte$/, '· $1 acts'],
    [/^(\d+(?:,\d+)?) (zile|luni|ani)$/, function(m){ return durata(m); }],
    [/^(\d+(?:,\d+)? (?:zile|luni|ani)) – (\d+(?:,\d+)? (?:zile|luni|ani)) · (\d+) acorduri( · alte (\d+) printr-un singur act)?$/,
      function(m, a, b, n, x, k){ return durata(a) + ' – ' + durata(b) + ' · ' + n + ' agreements' + (x ? ' · another ' + k + ' through a single act' : ''); }],
    [/^(\d+) acorduri$/, '$1 agreements'],
    [/^(\d)\. (.+)$/, function(m, n, e){ return ETAPA[e] ? n + '. ' + ETAPA[e] : null; }],
    [/^au trecut de etapa (\d+) din (\d+)$/, 'passed stage $1 of $2'],
    [/^din (\d+) acte publicate$/, 'of $1 published acts'],
    [/^Ultimii (\d+) ani$/, 'Last $1 years'],
    [/^Arată cele (\d+) de acorduri care au ajuns aici$/, 'Show the $1 agreements that reached this stage'],
    [/^Arată cele (\d+) acorduri care au ajuns aici$/, 'Show the $1 agreements that reached this stage'],
    [new RegExp('^În vigoare din ' + DATA + '$'), 'In force since $1'],
    [/^Vezi proiectele și sumele (.+) →$/, 'See $1 projects and amounts →'],
    [/^cu (\d+) mai puține decât la etapa anterioară — fie n-au ajuns încă aici, fie au urmat alt traseu$/, '$1 fewer than at the previous stage — they have either not got here yet or followed a different route'],
    [/^Excepțiile: anexa 1¹, pct\. (\d+) și (\d+)$/, 'Exceptions: annex 1¹, items $1 and $2'],
    [/^HG (\d+)\/(\d+), (.+)$/, function(m, a, b, r){ return 'Government Decision ' + a + '/' + b + ', ' + r.replace(/anexa nr\./g, 'annex no.').replace(/anexa/g, 'annex').replace(/pct\./g, 'item').replace(/cap\./g, 'ch.').replace(/ și /g, ' and '); }],
    [/^Un acord, un rând\. Actele din Registrul de stat al actelor juridice \(legis\.md\), (\d{4})–(\d{4}), grupate pe acordul din care fac parte, cu etapa la care a ajuns fiecare\.$/,
      'One agreement, one row. The acts from the State Register of Legal Acts (legis.md), $1–$2, grouped by the agreement they belong to, with the stage each agreement has reached.'],
    [/^acorduri pentru care inițierea negocierilor a fost publicată acum mai bine de un an, câte au ajuns la fiecare etapă\.(?: Alte (\d+) au început în ultimul an și nu sunt socotite — sunt încă pe drum\.)? Proiectul de lege și promulgarea privesc doar tratatele ratificate prin lege; acordurile aprobate prin hotărâre de Guvern sar peste ele\.$/,
      function(m, k){ return 'agreements whose start of negotiations was published more than a year ago: how many reached each stage.' + (k ? ' Another ' + k + ' started in the last year and are not counted — they are still under way.' : '') + ' The draft law and promulgation apply only to treaties ratified by law; agreements approved by Government decision skip them.'; }],
    [/^(Inițiere negocieri|Aprobare semnare|Aprobare proiect de lege|Ratificare sau aprobare|Decret de promulgare) — (.+)$/, function(m, e, r){
      r = r.replace(/^Etapă parcursă obligatoriu, dar fără act în registru — publicată cel mai probabil înainte de (\S+), de când începe acoperirea$/, 'Mandatory stage completed, but no act in the register — most likely published before $1, when coverage begins')
           .replace(/^Nu se aplică: acordul a fost aprobat prin hotărâre de Guvern/, 'Not applicable: the agreement was approved by Government decision')
           .replace(/Constituția, art\./, 'Constitution, art.').replace(/HG /g, 'GD ').replace(/pct\./g, 'item').replace(/anexa/g, 'annex').replace(/ și /g, ' and ');
      return ETAPA[e] + ' — ' + r; }],
    [/^Arhivă: $/, 'Archive: '],
    [/^(Categoria-părinte|Consultanță, instruire, expertiză|Asistență financiară rambursabilă|Asistență financiară nerambursabilă|Marcaj, nu categorie) \(pct\. ([\d.¹]+)\)$/, function(m, a, n){
      return ({'Categoria-părinte':'Parent category','Consultanță, instruire, expertiză':'Consultancy, training, expertise','Asistență financiară rambursabilă':'Reimbursable financial assistance',
               'Asistență financiară nerambursabilă':'Non-reimbursable financial assistance','Marcaj, nu categorie':'A marker, not a category'})[a] + ' (item ' + n + ')'; }],
    [/^Un acord parcurge cinci etape[\s\S]*$/, function(m){
      var y = /(\d{4})–(\d{4}), apoi filtrare/.exec(m);
      return "An agreement goes through five stages that can be followed act by act in the Official Gazette: the decision or decree starting negotiations, the approval to sign, the decision approving the draft law, the ratification law (or the approval decision, for agreements within the Government's competence) and the promulgation decree. Entry into force is not a sixth stage. The date shown under the stages is when the ratification law entered into force — its final article says the law enters into force on publication in the Gazette, which is the date of the edition. The agreement itself enters into force later, after the exchange of instruments of ratification; that date cannot be inferred from the contents, because the foreign minister's order announcing it is collective and does not name the agreement. Other mandatory stages — endorsement, initialling, full powers, the signing itself — produce no published act. Some of the agreements here are not international treaties but state contracts, which follow their own route: the contract category — with an impact on the state budget, on the authority's budget, with no budget impact, or inter-institutional cooperation — decides who approves it and when it enters into force. The financing types shown on the rows (grant, loan, credit, financing) are inferred from the act's title; their legal definitions are in the panel \"How an agreement is concluded\". Legal basis: Government Decision 442/2015, Government Decision 377/2018 with annexes 1 and 1¹, and Law no. 419/2006 for state loans. " + (y
        ? 'Source of this version: the State Register of Legal Acts (legis.md), searched by keywords in titles, year by year, ' + y[1] + '–' + y[2] + ', then filtered with the register\'s classifier, extended. The act number opens its page on legis.md.'
        : 'Source: the contents of the Official Gazette of the Republic of Moldova.'); }],
    [/^proiecte\. Raportul live nu a răspuns \((.+)\) — se lucrează doar cu arhiva, care acoperă până în (\d{4})\.$/, 'projects. The live report did not respond ($1) — working with the archive only, which covers up to $2.']
  ];

  var SARI = '.pname,.a-tit,.det-nume,.acte-list .a-tit,script,style,[data-no-tr]';
  // blocurile scrise în ambele limbi: se vede doar cel al limbii alese
  var st = document.createElement('style');
  st.textContent = 'html.lb-en [data-bloc="ro"]{display:none!important}html:not(.lb-en) [data-bloc="en"]{display:none!important}';
  document.head.appendChild(st);
  var orig = new WeakMap();     // nod text -> textul românesc
  var limba = 'ro';

  function traduce(t){
    var m = t.match(/^(\s*)([\s\S]*?)(\s*)$/), core = m[2].replace(/\s+/g, ' ');
    if (!core) return null;
    var r = EXACT[core];
    if (r === undefined){
      for (var i = 0; i < TIPARE.length; i++){
        var p = TIPARE[i], mm = core.match(p[0]);
        if (mm){ r = typeof p[1] === 'function' ? p[1].apply(null, mm) : core.replace(p[0], p[1]); if (r) break; }
      }
    }
    return r ? m[1] + r + m[3] : null;
  }
  function textNodes(root, fn){
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), n;
    var list = []; while ((n = w.nextNode())) list.push(n);
    list.forEach(fn);
  }
  function aplica(root){
    if (limba !== 'en') return;
    textNodes(root, function(n){
      var e = n.parentElement;
      if (!e || e.closest(SARI) || e.closest('.mg')) return;
      if (orig.has(n)) return;
      var r = traduce(n.nodeValue);
      if (r !== null){ orig.set(n, n.nodeValue); n.nodeValue = r; }
    });
    (root.querySelectorAll ? root.querySelectorAll('[placeholder],[title],[aria-label]') : []).forEach(function(e){
      if (e.closest('.mg')) return;
      ['placeholder', 'title', 'aria-label'].forEach(function(a){
        var v = e.getAttribute(a); if (!v || e.hasAttribute('data-ro-' + a)) return;
        var r = traduce(v); if (r !== null){ e.setAttribute('data-ro-' + a, v); e.setAttribute(a, r); }
      });
    });
  }
  function reface(){
    textNodes(document.body, function(n){ if (orig.has(n)){ n.nodeValue = orig.get(n); orig.delete(n); } });
    document.querySelectorAll('[data-ro-placeholder],[data-ro-title],[data-ro-aria-label]').forEach(function(e){
      ['placeholder', 'title', 'aria-label'].forEach(function(a){
        if (e.hasAttribute('data-ro-' + a)){ e.setAttribute(a, e.getAttribute('data-ro-' + a)); e.removeAttribute('data-ro-' + a); }
      });
    });
  }
  var titluRo = document.title;
  function seteaza(l){
    limba = l === 'en' ? 'en' : 'ro';
    document.documentElement.lang = limba;
    document.documentElement.classList.toggle('lb-en', limba === 'en');
    try { localStorage.setItem('limba', limba); } catch (e) {}
    if (limba === 'en'){ aplica(document.body); document.title = traduce(titluRo.split(' — ')[0]) ? traduce(titluRo.split(' — ')[0]) : titluRo; }
    else { reface(); document.title = titluRo; }
    if (window.Meniu) window.Meniu.limba(limba);
  }

  new MutationObserver(function(muts){
    if (limba !== 'en') return;
    muts.forEach(function(m){ m.addedNodes.forEach(function(n){
      if (n.nodeType === 1) aplica(n);
      else if (n.nodeType === 3 && n.parentElement && !orig.has(n)){ var r = traduce(n.nodeValue); if (r !== null && !n.parentElement.closest(SARI)){ orig.set(n, n.nodeValue); n.nodeValue = r; } }
    }); });
  }).observe(document.documentElement, {childList: true, subtree: true});

  window.Traducere = { seteaza: seteaza, limba: function(){ return limba; }, traduce: traduce };

  var ales = 'ro';
  try { ales = localStorage.getItem('limba') || 'ro'; } catch (e) {}
  var q = /[?&]lang=(en|ro)\b/.exec(location.search); if (q) ales = q[1];
  function start(){ if (ales === 'en') seteaza('en'); else if (window.Meniu) window.Meniu.limba('ro'); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
