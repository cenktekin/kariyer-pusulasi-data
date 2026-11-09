        let allDepartments = [];
        let selectedDepartments = [];
        let programData = {};
        const SELECTION_STORAGE_KEY = 'yokatlas_selected_departments';
        let sortBy = 'basari';
        let sortDirection = 'ASC';
        let filteredRowsGlobal = [];
        const DEFAULT_GUIDE_YEAR = 2026;
        let guideYear = DEFAULT_GUIDE_YEAR;

        const depSearch = document.getElementById('search-dep');
        const depListContainer = document.getElementById('dep-list-container');
        const activeDepsBar = document.getElementById('active-deps-bar');
        const tableBody = document.getElementById('table-body');
        const totalDepsCount = document.getElementById('total-departments-count');
        const filterPuanTuru = document.getElementById('filter-puan-turu');
        const filterDuration = document.getElementById('filter-duration');
        const filterType = document.getElementById('filter-type');
        const filterCity = document.getElementById('filter-city');
        const filterUcret = document.getElementById('filter-ucret');
        const filterSiraMax = document.getElementById('filter-sira-max');
        const filterPuanMin = document.getElementById('filter-puan-min');
        const searchUni = document.getElementById('search-uni');
        const noSelectedHint = document.getElementById('no-selected-hint');
        const filteredRatioBadge = document.getElementById('filtered-ratio-badge');
        const dataFreshness = document.getElementById('data-freshness');
        const thKontenjan = document.getElementById('th-kontenjan');
        const thSiralama = document.getElementById('th-siralama');
        const thPuan = document.getElementById('th-puan');

        function esc(value) {
            return String(value == null ? '' : value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function shortYear(year) {
            return String(year).slice(-2);
        }

        function applyYearLabels() {
            const y0 = guideYear;
            thKontenjan.innerText = `Kontenjan (${shortYear(y0)}/${shortYear(y0 - 1)}/${shortYear(y0 - 2)})`;
            thSiralama.innerText = `Başarı Sırası (${y0}) ↕`;
            thPuan.innerText = `Taban Puan (${y0}) ↕`;
        }

        function saveSelection() {
            try {
                localStorage.setItem(SELECTION_STORAGE_KEY, JSON.stringify(selectedDepartments));
            } catch (err) {
                console.error('Secim kaydedilemedi:', err);
            }
        }

        function readSavedSelection() {
            try {
                const raw = localStorage.getItem(SELECTION_STORAGE_KEY);
                const parsed = raw ? JSON.parse(raw) : [];
                return Array.isArray(parsed) ? parsed : [];
            } catch (err) {
                console.error('Kayitli secim okunamadi:', err);
                return [];
            }
        }

        async function restoreSelection() {
            const saved = readSavedSelection().filter(id => allDepartments.some(d => d.id === id));
            if (saved.length === 0) return;
            selectedDepartments = saved;
            await Promise.all(saved.map(id => programData[id] ? null : fetchDepartmentData(id)));
            renderDepartmentList(depSearch.value);
            renderActiveTags();
            renderTable();
        }

        async function loadMetadata() {
            try {
                const response = await fetch('/api/metadata');
                const meta = await response.json();
                if (meta) {
                    const parsedYear = parseInt(meta.guide_year, 10);
                    if (parsedYear > 2000 && parsedYear < 2100) {
                        guideYear = parsedYear;
                    }
                    applyYearLabels();
                }
                if (meta && meta.fetched_at) {
                    const d = new Date(meta.fetched_at);
                    dataFreshness.innerText = d.toLocaleDateString('tr-TR');
                    dataFreshness.parentElement.title =
                        `Kılavuz yılı: ${meta.guide_year || '-'} · ${meta.department_files || '-'} bölüm · ` +
                        `${(meta.total_programs || 0).toLocaleString('tr-TR')} program`;
                }
            } catch (err) {
                console.error('Veri meta bilgisi alinamadi:', err);
            }
        }

        window.addEventListener('DOMContentLoaded', async () => {
            applyYearLabels();
            await loadMetadata();
            await loadDepartments();
            await loadAllCities();
            await restoreSelection();
            setupEventListeners();
        });

        function getProgramDuration(facultyName) {
            const fac = facultyName.toLowerCase();
            if (fac.includes('meslek yüksek') || fac.includes('myo') || fac.endsWith('myo')) {
                return '2';
            }
            return '4';
        }

        async function loadDepartments() {
            try {
                const response = await fetch('/api/departments');
                allDepartments = await response.json();
                totalDepsCount.innerText = allDepartments.length;
                preloadAllDepartmentData();
            } catch (err) {
                console.error("Bölümler yüklenirken hata oluştu:", err);
                totalDepsCount.innerText = "Hata";
            }
        }

        async function preloadAllDepartmentData() {
            const chunk = 35;
            for (let i = 0; i < allDepartments.length; i += chunk) {
                const slice = allDepartments.slice(i, i + chunk);
                await Promise.all(slice.map(async (dep) => {
                    try {
                        const r = await fetch(`/api/department/${dep.id}`);
                        const res = await r.json();
                        programData[dep.id] = res.yks || [];
                    } catch(e) {
                        console.error(`Bolum verisi onden yuklenemedi (${dep.id}):`, e);
                    }
                }));
                renderDepartmentList(depSearch.value);
            }
        }

        // Helper to format Turkish character city names properly to uppercase
        function formatCityName(city) {
            if (!city) return '';
            // Standardize to uppercase with correct Turkish locale casing
            return city.trim().toLocaleUpperCase('tr-TR');
        }

        async function loadAllCities() {
            try {
                const response = await fetch('/api/cities');
                const rawCities = await response.json();
                
                // Deduplicate Turkish casing edge cases (like KOCAELİ vs Kocaeli or AFYON vs AFYONKARAHİSAR)
                const dedupedCities = new Set();
                rawCities.forEach(c => {
                    const formatted = formatCityName(c);
                    if (formatted) dedupedCities.add(formatted);
                });

                filterCity.innerHTML = '<option value="all">Tüm Şehirler</option>';
                Array.from(dedupedCities).sort((a,b) => a.localeCompare(b, 'tr')).forEach(city => {
                    const opt = document.createElement('option');
                    opt.value = city;
                    opt.innerText = city;
                    filterCity.appendChild(opt);
                });
            } catch (err) {
                console.error("Şehirler yüklenirken hata oluştu:", err);
            }
        }

        function getNormalizedText(txt) {
            return txt.toLocaleLowerCase('tr-TR');
        }

        function parseSiralamaVal(val) {
            if (!val || val === '-' || val === '') return Infinity;
            return parseInt(val.replace(/\./g, ''), 10);
        }

        function renderDepartmentList(filter = '') {
            depListContainer.innerHTML = '';
            
            const filteredByName = allDepartments.filter(d => 
                getNormalizedText(d.name).includes(getNormalizedText(filter))
            );

            const puanTuruVal = filterPuanTuru.value;
            const durationVal = filterDuration.value;
            const typeVal = filterType.value;
            const cityVal = filterCity.value;
            const ucretVal = filterUcret.value;
            const siraMaxVal = filterSiraMax.value ? parseInt(filterSiraMax.value, 10) : null;
            const puanMinVal = filterPuanMin.value ? parseFloat(filterPuanMin.value) : null;
            const uniSearchVal = getNormalizedText(searchUni.value);

            const isAnyFilterActive = (puanTuruVal !== 'all' || durationVal !== 'all' || typeVal !== 'all' || cityVal !== 'all' || ucretVal !== 'all' || siraMaxVal !== null || puanMinVal !== null || uniSearchVal !== '');

            let matchingCount = 0;

            filteredByName.forEach(dep => {
                const isSelected = selectedDepartments.includes(dep.id);
                
                let matchesFilters = true;
                const list = programData[dep.id];
                
                if (isAnyFilterActive) {
                    if (list) {
                        const hasMatchingProgram = list.some(item => {
                            if (puanTuruVal !== 'all' && item['Puan Türü'] !== puanTuruVal) return false;

                            const duration = getProgramDuration(item['Fakülte']);
                            if (durationVal !== 'all' && duration !== durationVal) return false;
                            if (typeVal !== 'all' && item['Üniversite Türü'] !== typeVal) return false;
                            
                            // Handle city check case-insensitively with Turkish characters normalization
                            if (cityVal !== 'all' && formatCityName(item['Şehir']) !== cityVal) return false;
                            
                            if (ucretVal !== 'all') {
                                if (ucretVal === 'Ücretli') {
                                    if (!(item['Ücret'] || '').includes('Ücretli')) return false;
                                } else if (item['Ücret'] !== ucretVal) {
                                    return false;
                                }
                            }
                            
                            if (siraMaxVal !== null) {
                                const rawSira = item['Taban Sıralama'] ? item['Taban Sıralama'][0] : '';
                                const siraNumeric = parseSiralamaVal(rawSira);
                                // If department rank is better (smaller number) than child's rank, child cannot enter
                                if (siraNumeric === Infinity || siraNumeric < siraMaxVal) return false;
                            }
                            
                            if (puanMinVal !== null) {
                                const rawPuan = item['Taban Puan'] ? item['Taban Puan'][0] : '';
                                const puanNumeric = rawPuan ? parseFloat(rawPuan) : 0;
                                // If department points requirement is higher than child's points, child cannot enter
                                if (puanNumeric > puanMinVal) return false;
                            }

                            if (uniSearchVal) {
                                const uniName = getNormalizedText(item['Üniversite']);
                                const progName = getNormalizedText(item['Program Adı']);
                                if (!uniName.includes(uniSearchVal) && !progName.includes(uniSearchVal)) return false;
                            }
                            return true;
                        });
                        matchesFilters = hasMatchingProgram;
                    } else {
                        matchesFilters = false; 
                    }
                }

                const el = document.createElement('div');
                el.className = `dep-item ${isSelected ? 'active' : ''} ${matchesFilters ? 'dep-item-match' : 'dep-item-no-match'}`;
                el.innerText = dep.name;
                el.title = dep.name;
                el.onclick = () => toggleDepartment(dep.id, dep.name);
                
                if (matchesFilters) {
                    matchingCount++;
                }
                
                depListContainer.appendChild(el);
            });

            filteredRatioBadge.innerText = `${matchingCount} / ${filteredByName.length}`;
        }

        function setupEventListeners() {
            depSearch.addEventListener('input', (e) => {
                renderDepartmentList(e.target.value);
            });

            const filters = [filterPuanTuru, filterDuration, filterType, filterCity, filterUcret];
            filters.forEach(f => {
                f.addEventListener('change', () => {
                    renderTable();
                    renderDepartmentList(depSearch.value);
                });
            });

            const inputs = [filterSiraMax, filterPuanMin, searchUni];
            inputs.forEach(i => {
                i.addEventListener('input', () => {
                    renderTable();
                    renderDepartmentList(depSearch.value);
                });
            });
        }

        async function toggleDepartment(id, name) {
            if (selectedDepartments.includes(id)) {
                selectedDepartments = selectedDepartments.filter(item => item !== id);
            } else {
                selectedDepartments.push(id);
                if (!programData[id]) {
                    await fetchDepartmentData(id);
                }
            }
            saveSelection();
            renderDepartmentList(depSearch.value);
            renderActiveTags();
            renderTable();
        }

        async function fetchDepartmentData(id) {
            try {
                const response = await fetch(`/api/department/${id}`);
                const data = await response.json();
                programData[id] = data.yks || [];
                renderDepartmentList(depSearch.value);
            } catch (err) {
                console.error(`Bölüm verisi alınamadı (${id}):`, err);
                programData[id] = [];
            }
        }

        function renderActiveTags() {
            const tags = activeDepsBar.querySelectorAll('.tag');
            tags.forEach(t => t.remove());

            if (selectedDepartments.length === 0) {
                noSelectedHint.style.display = 'inline';
                return;
            }
            noSelectedHint.style.display = 'none';

            selectedDepartments.forEach(id => {
                const depObj = allDepartments.find(d => d.id === id);
                if (!depObj) return;

                const tag = document.createElement('span');
                tag.className = 'tag';
                tag.appendChild(document.createTextNode(depObj.name));

                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.innerHTML = '&times;';
                removeBtn.setAttribute('aria-label', `${depObj.name} bölümünü listeden çıkar`);
                removeBtn.addEventListener('click', () => removeTag(id));
                tag.appendChild(removeBtn);

                activeDepsBar.appendChild(tag);
            });
        }

        // REMOVE TAG
        function removeTag(id) {
            selectedDepartments = selectedDepartments.filter(item => item !== id);
            saveSelection();
            renderDepartmentList(depSearch.value);
            renderActiveTags();
            renderTable();
        }

        // CLEAR ALL FILTERS AND SELECTIONS
        function clearAllFiltersAndSelection() {
            selectedDepartments = [];
            saveSelection();
            filterPuanTuru.value = 'all';
            filterDuration.value = 'all';
            filterType.value = 'all';
            filterCity.value = 'all';
            filterUcret.value = 'all';
            filterSiraMax.value = '';
            filterPuanMin.value = '';
            searchUni.value = '';
            depSearch.value = '';
            
            renderDepartmentList();
            renderActiveTags();
            renderTable();
        }

        function changeSort(field) {
            if (sortBy === field) {
                sortDirection = sortDirection === 'ASC' ? 'DESC' : 'ASC';
            } else {
                sortBy = field;
                sortDirection = field === 'basari' ? 'ASC' : 'DESC';
            }
            renderTable();
        }

        function renderTable() {
            tableBody.innerHTML = '';

            if (selectedDepartments.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="10" class="no-data">Analiz etmek istediğiniz bölümleri seçerek ekleyin. Aynı anda dilediğiniz kadar bölüm ekleyebilirsiniz!</td>
                    </tr>`;
                filteredRowsGlobal = [];
                return;
            }

            let rows = [];
            selectedDepartments.forEach(id => {
                const list = programData[id] || [];
                list.forEach(item => {
                    rows.push(item);
                });
            });

            const puanTuruVal = filterPuanTuru.value;
            const durationVal = filterDuration.value;
            const typeVal = filterType.value;
            const cityVal = filterCity.value;
            const ucretVal = filterUcret.value;
            const siraMaxVal = filterSiraMax.value ? parseInt(filterSiraMax.value, 10) : null;
            const puanMinVal = filterPuanMin.value ? parseFloat(filterPuanMin.value) : null;
            const uniSearchVal = getNormalizedText(searchUni.value);

            rows = rows.filter(item => {
                if (puanTuruVal !== 'all' && item['Puan Türü'] !== puanTuruVal) return false;
                const duration = getProgramDuration(item['Fakülte']);
                if (durationVal !== 'all' && duration !== durationVal) return false;
                if (typeVal !== 'all' && item['Üniversite Türü'] !== typeVal) return false;
                if (cityVal !== 'all' && formatCityName(item['Şehir']) !== cityVal) return false;
                if (ucretVal !== 'all') {
                    if (ucretVal === 'Ücretli') {
                        if (!(item['Ücret'] || '').includes('Ücretli')) return false;
                    } else if (item['Ücret'] !== ucretVal) {
                        return false;
                    }
                }
                
                if (siraMaxVal !== null) {
                    const rawSira = item['Taban Sıralama'] ? item['Taban Sıralama'][0] : '';
                    const siraNumeric = parseSiralamaVal(rawSira);
                    // If department rank is better (smaller number) than child's rank, child cannot enter
                    if (siraNumeric === Infinity || siraNumeric < siraMaxVal) return false;
                }
                
                if (puanMinVal !== null) {
                    const rawPuan = item['Taban Puan'] ? item['Taban Puan'][0] : '';
                    const puanNumeric = rawPuan ? parseFloat(rawPuan) : 0;
                    // If department points requirement is higher than child's points, child cannot enter
                    if (puanNumeric > puanMinVal) return false;
                }

                if (uniSearchVal) {
                    const uniName = getNormalizedText(item['Üniversite']);
                    const progName = getNormalizedText(item['Program Adı']);
                    if (!uniName.includes(uniSearchVal) && !progName.includes(uniSearchVal)) return false;
                }
                return true;
            });

            rows.sort((a, b) => {
                let valA, valB;
                
                if (sortBy === 'basari') {
                    const rawA = a['Taban Sıralama'] ? a['Taban Sıralama'][0] : '';
                    const rawB = b['Taban Sıralama'] ? b['Taban Sıralama'][0] : '';
                    
                    valA = parseSiralamaVal(rawA);
                    valB = parseSiralamaVal(rawB);
                } else {
                    const rawA = a['Taban Puan'] ? a['Taban Puan'][0] : '';
                    const rawB = b['Taban Puan'] ? b['Taban Puan'][0] : '';
                    
                    valA = rawA ? parseFloat(rawA) : 0;
                    valB = rawB ? parseFloat(rawB) : 0;
                }

                if (valA === valB) return 0;
                
                if (sortDirection === 'ASC') {
                    return valA > valB ? 1 : -1;
                } else {
                    return valA < valB ? 1 : -1;
                }
            });

            filteredRowsGlobal = rows;

            if (rows.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="10" class="no-data">Seçili filtrelerle eşleşen kayıt bulunamadı.</td>
                    </tr>`;
                return;
            }

            rows.forEach(item => {
                const tr = document.createElement('tr');
                const code = item['Program Kodu'];
                const uni = item['Üniversite'];
                const programName = item['Program Adı'];
                const faculty = item['Fakülte'];
                const type = item['Üniversite Türü'] || 'Devlet';
                const city = item['Şehir'];
                const ucret = item['Ücret'];
                const puanTuru = item['Puan Türü'] || '-';
                const duration = getProgramDuration(faculty);
                
                const k0 = item['Kontenjan'] ? item['Kontenjan'][0] : '-';
                const k1 = item['Kontenjan'] ? item['Kontenjan'][1] : '-';
                const k2 = item['Kontenjan'] ? item['Kontenjan'][2] : '-';

                const s0 = item['Taban Sıralama'] ? item['Taban Sıralama'][0] : '-';
                const s1 = item['Taban Sıralama'] ? item['Taban Sıralama'][1] : '-';
                const s2 = item['Taban Sıralama'] ? item['Taban Sıralama'][2] : '-';

                const p0 = item['Taban Puan'] ? item['Taban Puan'][0] : '-';
                
                let trendHTML = '';
                const parsedS0 = parseSiralamaVal(s0);
                const parsedS1 = parseSiralamaVal(s1);

                if (parsedS0 !== Infinity && parsedS1 !== Infinity) {
                    const diff = parsedS1 - parsedS0;
                    const absoluteDiff = Math.abs(diff).toLocaleString('tr-TR');
                    if (diff > 0) {
                        trendHTML = `<span class="trend-indicator trend-up" title="${guideYear - 1}'ten ${guideYear}'ya yükseliş trendi. Yerleşmek zorlaşmış.">▲ ${absoluteDiff} Sıra Zorlaşmış</span>`;
                    } else if (diff < 0) {
                        trendHTML = `<span class="trend-indicator trend-down" title="${guideYear - 1}'ten ${guideYear}'ya düşüş trendi. Yerleşmek kolaylaşmış.">▼ ${absoluteDiff} Sıra Kolaylaşmış</span>`;
                    }
                }

                const typeClass = type === 'Devlet' ? 'type-devlet' : 'type-vakif';
                const durationText = duration === '4' ? '4 Yıllık' : '2 Yıllık';
                const durationClass = duration === '4' ? 'duration-4' : 'duration-2';
                
                let ucretClass = '';
                const ucretText = ucret || '';
                if (ucretText === 'Burslu') ucretClass = 'ucret-burslu';
                else if (ucretText.includes('50')) ucretClass = 'ucret-50';
                else if (ucretText.includes('Ücretli')) ucretClass = 'ucret-ucretli';

                tr.innerHTML = `
                    <td class="val-code">${esc(code)}</td>
                    <td>
                        <div class="val-uni">${esc(uni)}</div>
                        <div class="val-dep">${esc(programName)} <span style="font-size: 0.8rem; color: var(--text-secondary);">(${esc(faculty)})</span></div>
                    </td>
                    <td><span class="badge-score-type">${esc(puanTuru)}</span></td>
                    <td><span class="badge-duration ${durationClass}">${esc(durationText)}</span></td>
                    <td><span class="badge-type ${typeClass}">${esc(type)}</span></td>
                    <td>${esc(city)}</td>
                    <td><span class="badge-ucret ${ucretClass}">${esc(ucret)}</span></td>
                    <td>
                        <span style="font-weight:600; color:var(--text-primary);">${esc(k0)}</span>
                        <span style="font-size:0.8rem; color:var(--text-secondary);"> / ${esc(k1)} / ${esc(k2)}</span>
                    </td>
                    <td>
                        <div class="val-sira">${esc(s0) || 'Dolmadı'}</div>
                        <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:0.15rem;">${guideYear - 1}: ${esc(s1) || '-'} | ${guideYear - 2}: ${esc(s2) || '-'}</div>
                        ${trendHTML}
                    </td>
                    <td class="val-puan">${esc(p0) || 'Dolmadı'}</td>
                `;
                tableBody.appendChild(tr);
            });
        }

        // EXPORT TO MARKDOWN
        function exportToMarkdown() {
            if (filteredRowsGlobal.length === 0) {
                alert("İndirilecek veri yok! Lütfen önce bölüm seçin ve filtreleyin.");
                return;
            }

            let md = `# YÖK Atlas Tercih Karşılaştırma Raporu\n\n`;
            md += `*Bu rapor yerel YÖK Atlas Analiz Karargahı tarafından üretilmiştir.*\n\n`;
            
            md += `### Uygulanan Filtreler:\n`;
            md += `* **Puan Türü:** ${filterPuanTuru.options[filterPuanTuru.selectedIndex].text}\n`;
            md += `* **Öğrenim Süresi:** ${filterDuration.options[filterDuration.selectedIndex].text}\n`;
            md += `* **Üniversite Türü:** ${filterType.options[filterType.selectedIndex].text}\n`;
            md += `* **Şehir:** ${filterCity.options[filterCity.selectedIndex].text}\n`;
            md += `* **Burs/Ücret:** ${filterUcret.options[filterUcret.selectedIndex].text}\n`;
            if (filterSiraMax.value) {
                md += `* **Maksimum Sıralama Limiti:** ${filterSiraMax.value}\n`;
            }
            if (filterPuanMin.value) {
                md += `* **Minimum Taban Puan Limiti:** ${filterPuanMin.value}\n`;
            }
            if (searchUni.value) {
                md += `* **Üniversite Filtresi:** "${searchUni.value}"\n`;
            }
            md += `\n---\n\n`;

            md += `| Kod | Üniversite / Bölüm | Tür | Süre | Tür | Şehir | Burs/Ücret | Kont. (${shortYear(guideYear)}/${shortYear(guideYear - 1)}/${shortYear(guideYear - 2)}) | Sıralama (${guideYear}) | Puan (${guideYear}) |\n`;
            md += `| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n`;

            filteredRowsGlobal.forEach(item => {
                const code = item['Program Kodu'];
                const uni = item['Üniversite'];
                const programName = item['Program Adı'];
                const faculty = item['Fakülte'];
                const type = item['Üniversite Türü'] || 'Devlet';
                const city = item['Şehir'];
                const ucret = item['Ücret'];
                const puanTuru = item['Puan Türü'] || '-';
                const duration = getProgramDuration(faculty) === '4' ? '4 Yıllık' : '2 Yıllık';
                
                const k0 = item['Kontenjan'] ? item['Kontenjan'][0] : '-';
                const k1 = item['Kontenjan'] ? item['Kontenjan'][1] : '-';
                const k2 = item['Kontenjan'] ? item['Kontenjan'][2] : '-';
                
                const s0 = item['Taban Sıralama'] ? item['Taban Sıralama'][0] : 'Dolmadı';
                const s1 = item['Taban Sıralama'] ? item['Taban Sıralama'][1] : '-';
                
                const puan = item['Taban Puan'] ? item['Taban Puan'][0] : 'Dolmadı';

                let trendTxt = "";
                const p0 = parseSiralamaVal(s0);
                const p1 = parseSiralamaVal(s1);
                if (p0 !== Infinity && p1 !== Infinity) {
                    const diff = p1 - p0;
                    trendTxt = diff > 0 ? ` (▲ ${Math.abs(diff).toLocaleString('tr-TR')} Sıra Zorlaştı)` : ` (▼ ${Math.abs(diff).toLocaleString('tr-TR')} Sıra Kolaylaştı)`;
                }

                const sanitizedDept = `${uni} - ${programName} (${faculty})`.replace(/\|/g, '\\|');
                const kontenjanStr = `${k0}/${k1}/${k2}`;
                
                md += `| ${code} | ${sanitizedDept} | ${puanTuru} | ${duration} | ${type} | ${city} | ${ucret || '-'} | ${kontenjanStr} | ${s0}${trendTxt} | ${puan} |\n`;
            });

            const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
            const link = document.createElement("a");
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", `yok-atlas-tercih-raporu.md`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    
