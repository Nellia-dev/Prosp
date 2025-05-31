import os
import sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError, Page, Browser, BrowserContext, Locator
import google.generativeai as genai
import time
import datetime
import json
import re
import traceback
from urllib.parse import urlparse

# --- Configuração Inicial ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OUTPUT_FOLDER = "harvester_output"
MAX_SEARCH_RETRIES_PER_GOOGLE_PAGE = 2
MAX_PAGES_TO_SCRAPE_GOOGLE = 5
MAX_RESULTS_PER_GOOGLE_PAGE_APPROX = 10

BROWSER_LAUNCH_TIMEOUT = 240000
EXTRACTION_BROWSER_LAUNCH_TIMEOUT = 75000
EXTRACTION_PAGE_NAVIGATION_TIMEOUT = 90000
EXTRACTION_NETWORKIDLE_TIMEOUT = 30000
EXTRACTION_DEFAULT_OPERATION_TIMEOUT = 60000
SOCIAL_MEDIA_EXTRACTION_PAUSE = 8000

GOOGLE_GOTO_TIMEOUT = 90000
GOOGLE_NETWORKIDLE_TIMEOUT = 120000
GOOGLE_COOKIE_CLICK_TIMEOUT = 7000
GOOGLE_SEARCHBOX_TIMEOUT = 15000
GOOGLE_RESULTS_WAIT_TIMEOUT = 60000
GOOGLE_PAGINATION_CLICK_TIMEOUT = 30000

GEMINI_REQUEST_TIMEOUT = 300
GEMINI_MAX_TEXT_INPUT_CHARS = 25000

if not GOOGLE_API_KEY:
    print("Erro CRÍTICO: A variável de ambiente GOOGLE_API_KEY não foi definida.")
    sys.exit(1)

gemini_model_multimodal = None
# ATENÇÃO: Configurando 'gemini-2.0-flash' conforme solicitado.
# Este modelo NÃO é multimodal e a análise de imagem provavelmente FALHARÁ.
MODEL_NAME_FOR_IMAGE_ANALYSIS = 'gemini-2.0-flash'
try:
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    print(f"Pasta de saída '{OUTPUT_FOLDER}' verificada/criada.")
    genai.configure(api_key=GOOGLE_API_KEY)

    print(f"Tentando configurar o modelo Gemini para análise de imagem: {MODEL_NAME_FOR_IMAGE_ANALYSIS}")
    # A configuração do modelo ainda será tentada. O erro ocorrerá ao tentar usá-lo com imagem.
    gemini_model_multimodal = genai.GenerativeModel(MODEL_NAME_FOR_IMAGE_ANALYSIS)
    print(f"API do Gemini (modelo para imagem: '{MODEL_NAME_FOR_IMAGE_ANALYSIS}') configurada com sucesso.")
    print(f"AVISO: O modelo '{MODEL_NAME_FOR_IMAGE_ANALYSIS}' provavelmente não suporta entrada de imagem. A análise multimodal pode falhar.")

except Exception as e:
    print(f"Erro CRÍTICO durante a configuração inicial do Gemini para imagem: {e}")
    traceback.print_exc()

def get_domain_from_url(url: str) -> str:
    try: return urlparse(url).netloc
    except: return ""

def make_safe_filename(text: str, max_len: int = 50) -> str:
    text = re.sub(r'[^\w\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '-', text)
    return text[:max_len]

def get_screenshot_bytes(page: Page, full_page: bool = False) -> bytes | None:
    try:
        if page.is_closed(): return None
        return page.screenshot(full_page=full_page, type="png")
    except Exception as e:
        print(f"  Aviso: Falha ao obter screenshot: {e}")
        return None

def ask_gemini_about_image(image_bytes: bytes, prompt_text: str, attempt: int = 1) -> str | None:
    if not gemini_model_multimodal:
        print("  [IA Imagem] Modelo Gemini para imagem não configurado. Pulando análise.")
        return "FALHA IA IMAGEM: Modelo não configurado."
    if not image_bytes:
        print("  [IA Imagem] Nenhum byte de imagem fornecido.")
        return None
    print(f"  [IA Imagem, Tentativa {attempt}] Enviando imagem e prompt para Gemini ({MODEL_NAME_FOR_IMAGE_ANALYSIS})...")
    try:
        image_part = {"mime_type": "image/png", "data": image_bytes}
        # A API generate_content para modelos de texto puro não aceita 'image_part' desta forma.
        # Isso provavelmente causará um erro na chamada da API.
        content_parts = [prompt_text, image_part]
        generation_config = genai.types.GenerationConfig(temperature=0.2, max_output_tokens=350)
        safety_settings = [
            {"category": genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE},
            {"category": genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE},
            {"category": genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE},
            {"category": genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE},
        ]
        response = gemini_model_multimodal.generate_content(
            content_parts, # Esta linha causará erro se o modelo não for multimodal
            generation_config=generation_config, safety_settings=safety_settings,
            request_options={"timeout": GEMINI_REQUEST_TIMEOUT}
        )
        if not response.candidates or response.prompt_feedback.block_reason:
            reason = response.prompt_feedback.block_reason_message or str(response.prompt_feedback.block_reason)
            print(f"  [IA Imagem] ERRO: Prompt bloqueado. Razão: {reason}")
            return f"FALHA IA IMAGEM: Prompt bloqueado - {reason}"
        print("  [IA Imagem] Resposta da IA recebida.")
        return response.text.strip()
    except Exception as e:
        print(f"  [IA Imagem] ERRO ao interagir com Gemini ({MODEL_NAME_FOR_IMAGE_ANALYSIS}): {type(e).__name__} - {e}")
        error_str = str(e).lower()
        # Erros esperados se 'gemini-2.0-flash' for usado com imagem:
        if "model does not support image input" in error_str or \
           "invalid argument" in error_str or \
           "media type image/png is not supported" in error_str or \
           "could not parse request body" in error_str: # Erro comum quando a estrutura do payload está errada para o modelo
            print(f"  [IA Imagem] ERRO ESPERADO: O modelo '{MODEL_NAME_FOR_IMAGE_ANALYSIS}' não suporta entrada de imagem.")
            return f"FALHA IA IMAGEM: Modelo {MODEL_NAME_FOR_IMAGE_ANALYSIS} não suporta imagem."
        if any(s in error_str for s in ["model analytics", "user location is not supported",
                                        "must have a `model` name",
                                        "400 an input image token count exceeds the limit",
                                        "model is overloaded", "try again later", "resource has been exhausted"
                                        ]):
            print(f"  [IA Imagem] ERRO: {e}")
            return f"FALHA IA IMAGEM: {MODEL_NAME_FOR_IMAGE_ANALYSIS} - {type(e).__name__}."
        return f"FALHA IA IMAGEM: {type(e).__name__} - {e}"


def extract_google_result_data(link_element_locator: Locator) -> dict | None:
    try:
        if not link_element_locator.is_visible(timeout=500):
            return None
        href = link_element_locator.get_attribute("href")
        if not href or not href.startswith("http") or "google.com/search?q=related:" in href or "webcache.googleusercontent.com" in href:
            return None

        title_text = ""
        try:
            h3_inside_a = link_element_locator.locator('h3').first
            if h3_inside_a.count() > 0 and h3_inside_a.is_visible(timeout=100):
                title_text = h3_inside_a.inner_text(timeout=100).strip()

            if not title_text:
                text_content = link_element_locator.text_content(timeout=100)
                if text_content:
                    cleaned_text_content = ' '.join(text_content.split()).strip()
                    if cleaned_text_content and len(cleaned_text_content) < 200 and '\n' not in text_content[:200]:
                         title_text = cleaned_text_content
            if not title_text:
                return None
        except PlaywrightError:
            return None

        snippet = ""
        # Contêineres de resultado. Removido 'div. सोPav' que estava causando erro.
        parent_container = link_element_locator.locator(
            "xpath=./ancestor::div[contains(@class,'MjjYud') or contains(@class,'g') or contains(@class,'kvH3mc') or contains(@class,'tF2Cxc') or contains(@class,'hlcw0c') or contains(@class,'Gx5Zad')][1]"
        ).first

        if parent_container.count() > 0:
            snippet_selectors = [
                "div.VwiC3b", "div.MUxGbd", "div.yyu7Pd", "div.gJBeNe",
                "div[data-sncf='1']", "div[data-snc='2']",
                "div.Uroaid", "div.w15G8d", # Removido span. शहीदต que é muito específico e pode não ser universal
                ".s3v9rd > div > span", ".st", "div[role='text']",
                "div.djdOE", "div.f1GfJe", "div.P8vmC", "div.zz3gNc",
                "span.A03XMd",
                # Adicionar seletores de descrição de meta tag se o snippet direto falhar (mais avançado, requer acesso ao head)
                # "div[data-content-feature='1']", "div[data-content-feature='2']" # Outras estruturas data-*
            ]
            temp_snippet_parts = []
            for sel in snippet_selectors:
                snippet_elements = parent_container.locator(sel).all()
                if snippet_elements:
                    for snip_el in snippet_elements:
                        try:
                            if snip_el.is_visible(timeout=50):
                                text_part = snip_el.inner_text(timeout=50).strip()
                                if text_part and len(text_part) > 10:
                                    temp_snippet_parts.append(text_part)
                        except PlaywrightError: continue
            
            if temp_snippet_parts:
                snippet = " ".join(temp_snippet_parts).strip()
                if snippet.lower().startswith(title_text.lower()):
                    snippet = snippet[len(title_text):].strip(" .-").strip()
                if len(snippet) < 20: # Se o snippet ficar muito curto após remover o título
                    snippet = "" # Reseta para tentar o fallback

            if not snippet or len(snippet) < 20: # Se ainda sem snippet ou muito curto
                try:
                    all_text_in_container = parent_container.inner_text(timeout=200).strip()
                    snippet_candidate = all_text_in_container.replace(title_text, "").strip()
                    url_domain = get_domain_from_url(href); url_path = urlparse(href).path
                    if url_domain: snippet_candidate = snippet_candidate.replace(url_domain, "").strip()
                    if url_path and len(url_path) > 1 : snippet_candidate = snippet_candidate.replace(url_path, "").strip()
                    snippet_candidate = snippet_candidate.replace(href, "").strip()
                    snippet_candidate = re.sub(r'\s*\n\s*', ' ', snippet_candidate).strip()
                    snippet_candidate = re.sub(r'\s{2,}', ' ', snippet_candidate)
                    
                    if '...' in snippet_candidate:
                        parts_around_ellipsis = [p.strip() for p in snippet_candidate.split('...') if p.strip() and len(p.strip()) > 10]
                        if parts_around_ellipsis:
                            snippet = " ... ".join(parts_around_ellipsis[:2])
                        else:
                            snippet = snippet_candidate
                    else:
                        snippet = snippet_candidate

                    if len(snippet) > 250: snippet = snippet[:snippet.rfind(' ', 0, 250)] + "..."
                    if len(snippet) < 20 : snippet = "Snippet não claramente identificado via fallback."
                except PlaywrightError:
                    snippet = "Erro ao processar snippet fallback."
        
        return {"url": href, "title": title_text, "snippet": snippet or "Snippet não extraído."}
    except Exception:
        return None

def extract_links_from_google_page(page: Page, num_links_target: int, collected_urls_set: set) -> list[dict]:
    newly_found_results_data = []
    print(f"    [Google Page] Extraindo dados dos resultados (URL, título, snippet)...")

    result_block_selectors = [
        "div.g", "div.MjjYud", "div.tF2Cxc", "div.kvH3mc",
        "div.hlcw0c", "div.Gx5Zad", "div.srQUdf",
        "div[jscontroller][data-hveid][data-ved]"
        # Removido 'div. सोPav' que causava erro de parsing.
    ]
    main_link_selectors_in_block = [
        'a[href^="http"]:has(h3):visible:not([href*="google.com/search"]):not([href*="webcache.googleusercontent.com"])',
        'div.yuRUbf > a[href^="http"]:visible:not([href*="google.com/search"]):not([href*="webcache.googleusercontent.com"])',
        'div[class="r"] > a[href^="http"]:visible:not([href*="google.com/search"]):not([href*="webcache.googleusercontent.com"])',
        'h3 > a[href^="http"]:visible:not([href*="google.com/search"]):not([href*="webcache.googleusercontent.com"])',
        'a[href^="http"][role="link"]:visible:not([href*="google.com/search"]):not([href*="webcache.googleusercontent.com"]):not([jsname])'
    ]

    candidate_link_locators: list[Locator] = []
    total_blocks_inspected = 0

    for res_block_sel in result_block_selectors:
        if page.is_closed(): break
        try:
            blocks = page.locator(res_block_sel).all()
            total_blocks_inspected += len(blocks)
            for block_element in blocks:
                if page.is_closed(): break
                found_link_in_block = False
                for link_sel_in_block in main_link_selectors_in_block:
                    try:
                        link_loc = block_element.locator(link_sel_in_block).first
                        if link_loc.count() > 0 and link_loc.is_visible(timeout=100):
                            candidate_link_locators.append(link_loc)
                            found_link_in_block = True
                            break
                    except PlaywrightError:
                        continue
        except PlaywrightError as e:
            # A mensagem de erro sobre 'div. सोPav' será evitada agora
            if 'Unexpected token " " while parsing css selector' not in str(e):
                 print(f"      Aviso: Erro ao processar seletor de bloco '{res_block_sel}': {e}")

    print(f"      Total de blocos de resultado potenciais inspecionados: {total_blocks_inspected}.")
    if not candidate_link_locators:
        print("      Nenhum locator de link candidato encontrado. Verifique os seletores de bloco e link, e o screenshot de depuração.")
        if page and not page.is_closed():
            page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_no_candidate_links_found.png"))
            print(f"        Screenshot salvo: debug_google_no_candidate_links_found.png")
        return []

    unique_locators_by_href: dict[str, Locator] = {}
    for loc in candidate_link_locators:
        if page.is_closed(): break
        try:
            href_attr = loc.get_attribute("href", timeout=200)
            if href_attr and href_attr not in unique_locators_by_href:
                unique_locators_by_href[href_attr] = loc
        except PlaywrightError:
            continue

    final_candidate_locators = list(unique_locators_by_href.values())
    print(f"      Encontrados {len(final_candidate_locators)} elementos <a> únicos candidatos a link principal.")

    for link_locator in final_candidate_locators:
        if page.is_closed() or len(collected_urls_set) + len(newly_found_results_data) >= num_links_target:
            break
        result_data = extract_google_result_data(link_locator)
        if result_data:
            domain = get_domain_from_url(result_data["url"])
            excluded_domains = [
                "google.com", "youtube.com", "facebook.com", "instagram.com", "twitter.com", "linkedin.com",
                "wikipedia.org", "wikimedia.org", ".gov", ".mil", ".edu", # Note .gov e .edu aqui para TLDs
                "amazon.", "ebay.", "mercadolivre.", "shopee.",
                "support.", "policies.", "maps.", "accounts.", "translate.", "books.", "patents.", "drive.", "play.", "news.", "scholar.", "images.", "search."
            ]
            is_excluded = False
            # Verificar se o domínio termina com .gov, .mil, .edu
            if any(domain.endswith(suffix) for suffix in [".gov", ".mil", ".edu"]):
                 is_excluded = True
            else: # Verificar os outros domínios por inclusão
                for ex_domain_part in excluded_domains:
                    if ex_domain_part.startswith(".") : continue # Já tratado acima
                    if ex_domain_part in domain:
                        is_excluded = True; break
            
            if is_excluded or result_data["url"] in collected_urls_set:
                continue
            newly_found_results_data.append(result_data)

    print(f"    [Google Page] {len(newly_found_results_data)} resultados novos e únicos (com dados) extraídos desta página.")
    if len(newly_found_results_data) == 0 and len(final_candidate_locators) > 0:
        print("      AVISO: Foram encontrados links candidatos, mas nenhum passou nos filtros de extração de dados (título/snippet/exclusão).")
        if page and not page.is_closed():
            page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_candidates_filtered_out.png"))
            print(f"        Screenshot salvo: debug_google_candidates_filtered_out.png")
    return newly_found_results_data


# --- Função search_google_and_get_top_n_links (sem alterações significativas além das chamadas acima) ---
def search_google_and_get_top_n_links(query: str, num_links_target: int = 25) -> list[dict]:
    all_collected_results_data = []
    processed_urls_set = set()

    print(f"\nBuscando no Google por: '{query}' para obter até {num_links_target} resultados.")
    print(f"  (Máximo {MAX_SEARCH_RETRIES_PER_GOOGLE_PAGE} tentativas por página, até {MAX_PAGES_TO_SCRAPE_GOOGLE} páginas do Google)")

    with sync_playwright() as p_instance:
        browser: Browser | None = None
        context: BrowserContext | None = None
        page: Page | None = None
        try:
            print(f"  Iniciando navegador para busca Google (timeout: {BROWSER_LAUNCH_TIMEOUT / 1000}s)...")
            browser = p_instance.chromium.launch(headless=False, timeout=BROWSER_LAUNCH_TIMEOUT)
            print("  Navegador para busca Google iniciado.")
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                java_script_enabled=True, ignore_https_errors=True, accept_downloads=False,
                viewport={'width': 1366, 'height': 768}
            )
            page = context.new_page()
            print("  Contexto e página para busca Google criados.")

            print("  Navegando para Google.com...")
            navigation_successful = False
            google_url = "https://www.google.com/ncr"
            for wait_type in ["domcontentloaded", "load", "networkidle"]:
                if navigation_successful: break
                print(f"    Tentando carregar {google_url} (wait_until='{wait_type}', timeout={GOOGLE_NETWORKIDLE_TIMEOUT/1000}s)...")
                try:
                    page.goto(google_url, timeout=GOOGLE_GOTO_TIMEOUT, wait_until=wait_type) # type: ignore
                    navigation_successful = True; print(f"    Página do Google carregada com '{wait_type}'."); break
                except PlaywrightTimeoutError as e_goto: print(f"      Timeout no goto (wait_until='{wait_type}'): {e_goto}")
                except Exception as e_goto_general: print(f"      Erro inesperado no goto (wait_until='{wait_type}'): {type(e_goto_general).__name__} - {e_goto_general}")

            if not navigation_successful:
                print("    Todas as estratégias de goto falharam. Tentando um reload final...")
                try:
                    page.reload(timeout=GOOGLE_NETWORKIDLE_TIMEOUT, wait_until="domcontentloaded") # type: ignore
                    print("    Página do Google recarregada com sucesso."); navigation_successful = True
                except Exception as e_reload:
                    print(f"      Falha crítica ao tentar recarregar Google.com: {e_reload}")
                    raise PlaywrightError(f"Falha crítica ao carregar Google.com: {e_reload}") from e_reload

            if not navigation_successful: raise PlaywrightError("Não foi possível carregar Google.com.")
            print("  Página do Google carregada.")

            cookie_selectors = [
                'button:has-text("Accept all")', 'button:has-text("Aceitar tudo")',
                'button:has-text("Concordo")', 'button:has-text("I agree")',
                'div[role="dialog"] button:has-text("Aceitar")', 'button[id="L2AGLb"]',
                'button:has-text("Reject all")', 'button:has-text("Rejeitar tudo")',
                'button:has-text("Personalizar") ~ button:not(:has-text("Personalizar"))',
                'button[aria-label*="Aceitar"]', 'button[aria-label*="Accept"]',
            ]
            cookie_handled = False
            for sel_idx, sel in enumerate(cookie_selectors):
                if page.is_closed(): break
                try:
                    timeout_cookie = GOOGLE_COOKIE_CLICK_TIMEOUT if sel_idx == 0 else 2000
                    cookie_button = page.locator(sel).first
                    if cookie_button.is_visible(timeout=timeout_cookie):
                        print(f"    Clicando no botão de cookies (seletor {sel_idx+1}): '{sel}'");
                        cookie_button.click(timeout=3000)
                        page.wait_for_timeout(2000);
                        cookie_handled = True; break
                except PlaywrightError: pass
            if not cookie_handled and not page.is_closed():
                 print("    Nenhum pop-up de cookie proeminente encontrado ou tratado pelos seletores principais.")
            if page.is_closed(): print("  ERRO: Página fechada após cookies."); return []


            print(f"  Digitando termo de busca: '{query}'")
            search_box_interaction_sel = 'textarea[name="q"][role="combobox"], input[name="q"]:not([type="hidden"])'
            try:
                search_box_locator = page.locator(search_box_interaction_sel).first
                search_box_locator.wait_for(state="visible", timeout=GOOGLE_SEARCHBOX_TIMEOUT)
                search_box_locator.fill(query)
                page.wait_for_timeout(1000)
                search_box_locator.press("Enter")
                print("  Termo de busca enviado.")
            except PlaywrightError as e_searchbox:
                print(f"    ERRO: Não foi possível interagir com a caixa de busca (seletor: {search_box_interaction_sel}). {e_searchbox}")
                if page and not page.is_closed(): page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_searchbox_fail.png"))
                raise

            page_content_issue_screenshot_taken_this_serp = False
            for page_num in range(1, MAX_PAGES_TO_SCRAPE_GOOGLE + 1):
                if page.is_closed() or len(all_collected_results_data) >= num_links_target: break
                print(f"\n  --- Processando Página {page_num} do Google ---")
                current_page_had_results = False
                page_content_issue_screenshot_taken_this_serp = False

                if page_num == 1: page.wait_for_timeout(3000) # Aumentado para primeira página
                else: page.wait_for_timeout(2000)

                for attempt in range(1, MAX_SEARCH_RETRIES_PER_GOOGLE_PAGE + 1):
                    print(f"    [Página {page_num}, Tentativa {attempt}] Aguardando e verificando resultados...")
                    wait_for_content_or_end_selector = (
                        '#main, #rcnt, #center_col, #search, '
                        '#botstuff, '
                        'div:text-matches("(Nenhum resultado encontrado para|No results found for|não encontrou nenhum resultado para|did not match any documents|Sua pesquisa não encontrou nenhum documento correspondente)", "i")'
                    )
                    try:
                        page.locator(wait_for_content_or_end_selector).first.wait_for(state="visible", timeout=GOOGLE_RESULTS_WAIT_TIMEOUT)
                        print(f"      Contêiner de resultados/fim da página {page_num} visível.")
                        page.wait_for_timeout(2000 + (700 * attempt)) # Aumentado

                        if page.is_closed(): raise PlaywrightError("Página fechada inesperadamente")

                        no_results_locator = page.locator('div:text-matches("(Nenhum resultado encontrado para|No results found for|não encontrou nenhum resultado para|did not match any documents|Sua pesquisa não encontrou nenhum documento correspondente)", "i")')
                        is_explicit_no_results_message = False
                        if no_results_locator.count() > 0:
                            try:
                                if no_results_locator.first.is_visible(timeout=1000):
                                    is_explicit_no_results_message = True
                                    print(f"      Detectada mensagem explícita de 'nenhum resultado' do Google: '{no_results_locator.first.text_content(timeout=500)}'")
                            except PlaywrightError:
                                print("      Aviso: Locator de 'nenhum resultado' encontrado no DOM, mas não visível.")


                        if not is_explicit_no_results_message and page.locator("div.g, div.MjjYud, div.tF2Cxc").count() == 0 :
                            print(f"      AVISO: Nenhum bloco de resultado inicial (div.g, MjjYud, tF2Cxc) encontrado na página {page_num}, tentativa {attempt}.")
                            if not page_content_issue_screenshot_taken_this_serp:
                                page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_no_main_result_blocks_page{page_num}_attempt{attempt}.png"))
                                print(f"        Screenshot salvo: debug_google_no_main_result_blocks_page{page_num}_attempt{attempt}.png")
                                page_content_issue_screenshot_taken_this_serp = True
                            if attempt < MAX_SEARCH_RETRIES_PER_GOOGLE_PAGE: continue
                            else: current_page_had_results = False; break

                        new_results_data = extract_links_from_google_page(page, num_links_target, processed_urls_set)

                        if new_results_data:
                            current_page_had_results = True
                            added_count_this_page = 0
                            for res_data in new_results_data:
                                if res_data["url"] not in processed_urls_set:
                                    processed_urls_set.add(res_data["url"])
                                    all_collected_results_data.append(res_data)
                                    added_count_this_page +=1
                                if len(all_collected_results_data) >= num_links_target: break
                            print(f"      Adicionados {added_count_this_page} resultados novos. Total: {len(all_collected_results_data)}.")
                            if len(all_collected_results_data) >= num_links_target: break
                            break
                        elif is_explicit_no_results_message:
                            print(f"      Fim dos resultados do Google confirmado por mensagem na página {page_num}.")
                            current_page_had_results = False; break
                        else:
                            print(f"      Nenhum resultado novo qualificado extraído na tentativa {attempt} da página {page_num}.")
                            if attempt == MAX_SEARCH_RETRIES_PER_GOOGLE_PAGE:
                                print(f"        Máximo de tentativas para página {page_num} sem conseguir extrair resultados qualificados.")
                                if page and not page.is_closed() and not page_content_issue_screenshot_taken_this_serp:
                                    page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_no_qualified_results_page{page_num}.png"))
                                    print(f"        Screenshot salvo: debug_google_no_qualified_results_page{page_num}.png")
                                current_page_had_results = False

                    except PlaywrightTimeoutError:
                        print(f"      Timeout esperando por contêiner/resultados/fim na página {page_num}, tentativa {attempt}.")
                        if page and not page.is_closed() and not page_content_issue_screenshot_taken_this_serp:
                            page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_timeout_results_page{page_num}_attempt{attempt}.png"))
                            print(f"        Screenshot salvo: debug_google_timeout_results_page{page_num}_attempt{attempt}.png")
                            page_content_issue_screenshot_taken_this_serp = True
                        if attempt == MAX_SEARCH_RETRIES_PER_GOOGLE_PAGE: current_page_had_results = False
                    except PlaywrightError as e_page_attempt:
                        print(f"      Erro Playwright na tentativa {attempt} da página {page_num}: {e_page_attempt}")
                        if page and not page.is_closed() and not page_content_issue_screenshot_taken_this_serp:
                            page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_page{page_num}_attempt{attempt}_playwright_fail.png"))
                            print(f"        Screenshot salvo: debug_google_page{page_num}_attempt{attempt}_playwright_fail.png")
                            page_content_issue_screenshot_taken_this_serp = True
                        if attempt == MAX_SEARCH_RETRIES_PER_GOOGLE_PAGE: current_page_had_results = False
                    except Exception as e_general_attempt:
                        print(f"      Erro inesperado na tentativa {attempt} da página {page_num}: {type(e_general_attempt).__name__} - {e_general_attempt}")
                        traceback.print_exc()
                        if attempt == MAX_SEARCH_RETRIES_PER_GOOGLE_PAGE: current_page_had_results = False

                final_check_no_results_locator = page.locator('div:text-matches("(Nenhum resultado encontrado para|No results found for|não encontrou nenhum resultado para|did not match any documents|Sua pesquisa não encontrou nenhum documento correspondente)", "i")')
                final_is_explicit_no_results_message = False
                if not page.is_closed() and final_check_no_results_locator.count() > 0: # Adicionado page.is_closed() check
                    try:
                        if final_check_no_results_locator.first.is_visible(timeout=500):
                             final_is_explicit_no_results_message = True
                    except PlaywrightError: pass


                if not current_page_had_results:
                    if final_is_explicit_no_results_message:
                        print(f"  Fim dos resultados ou nenhum resultado encontrado (confirmado por mensagem) na página {page_num}. Interrompendo paginação.")
                    else:
                        print(f"  Nenhum resultado processável na página {page_num} após todas as tentativas e NENHUMA mensagem explícita de 'fim dos resultados'. Interrompendo paginação.")
                        if page and not page.is_closed() and not page_content_issue_screenshot_taken_this_serp:
                            page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_page{page_num}_giving_up_no_results_final.png"))
                            print(f"    Screenshot salvo: debug_google_page{page_num}_giving_up_no_results_final.png")
                    break

                if len(all_collected_results_data) >= num_links_target: break

                if page_num < MAX_PAGES_TO_SCRAPE_GOOGLE:
                    print(f"    Tentando navegar para a próxima página...")
                    navigated_to_next_page_sel = False
                    next_page_selectors = [
                        'a#pnnext', 'a[aria-label="Próxima página"]', 'a[aria-label="Next page"]',
                        'a[aria-label="Mais resultados"]', 'a[aria-label="More results"]',
                        '#pnnext > span.SJajHc', 'table.AaVjTc td.YyVfkd a.fl:has(span:text-matches("Próxima|Next", "i"))',
                        'span:text-matches("Mais|Next", "i") + a',
                        'a:has(span:text-matches("Próxima|Next", "i"))'
                    ]
                    for next_sel_idx, next_sel in enumerate(next_page_selectors):
                        if page.is_closed(): break
                        try:
                            next_button_candidate = page.locator(next_sel)
                            if next_button_candidate.count() > 0:
                                btn_to_click = next_button_candidate.first
                                if btn_to_click.is_visible(timeout=2000):
                                    print(f"      Clicando 'Próxima' (seletor {next_sel_idx+1}: '{next_sel}')...");
                                    btn_to_click.click(timeout=GOOGLE_PAGINATION_CLICK_TIMEOUT)
                                    page.wait_for_load_state("domcontentloaded", timeout=GOOGLE_PAGINATION_CLICK_TIMEOUT + 5000)
                                    print("      Navegado para próxima página (ou tentativa).");
                                    page.wait_for_timeout(2000 + (500 * page_num)) # Aumentado
                                    navigated_to_next_page_sel = True; break
                        except PlaywrightError:
                            pass
                    if page.is_closed(): print("  ERRO: Página fechada ao tentar paginar."); break
                    if not navigated_to_next_page_sel:
                        print("    Não foi possível paginar com seletores conhecidos. Verifique screenshot. Fim da busca.")
                        if page and not page.is_closed(): page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_pagination_fail_page{page_num}.png"))
                        break
                else:
                    print("  Limite de páginas do Google atingido."); break
        except Exception as e_google_search:
            print(f"Erro CRÍTICO na busca Google: {type(e_google_search).__name__} - {e_google_search}")
            traceback.print_exc()
            if page and not page.is_closed():
                page.screenshot(path=os.path.join(OUTPUT_FOLDER, f"debug_google_critical_error_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"))
        finally:
            print("  Finalizando sessão de busca Google...")
            if page and not page.is_closed():
                try: page.close()
                except Exception: pass
            if context:
                try: context.close()
                except Exception: pass
            if browser and browser.is_connected():
                try: browser.close()
                except Exception: pass
            print("  Sessão de busca Google finalizada.")

    print(f"\nBusca no Google concluída. Total de {len(all_collected_results_data)} resultados (URL, título, snippet) coletados.")
    return all_collected_results_data[:num_links_target]

# --- extract_text_from_url (sem alterações aqui, o modelo já foi definido no início) ---
def extract_text_from_url(url: str) -> tuple[str | None, str | None, str | None]:
    extracted_text_dom = None
    final_screenshot_path = None
    print(f"\n[Extração] Iniciando para URL: {url}")

    domain = get_domain_from_url(url)
    is_social_media = "instagram.com" in domain or "linkedin.com" in domain
    timestamp_url_part = make_safe_filename(urlparse(url).path if urlparse(url).path else "homepage")

    page_screenshot_filename = f"screenshot_extract_{make_safe_filename(domain)}_{timestamp_url_part}_{datetime.datetime.now().strftime('%H%M%S')}.png"
    page_screenshot_path_candidate = os.path.join(OUTPUT_FOLDER, page_screenshot_filename)

    with sync_playwright() as p_instance:
        browser_extract: Browser | None = None
        context_extract: BrowserContext | None = None
        page_extract: Page | None = None
        try:
            print(f"  [Extração] Lançando navegador (timeout: {EXTRACTION_BROWSER_LAUNCH_TIMEOUT/1000}s)...")
            browser_extract = p_instance.chromium.launch(headless=False, timeout=EXTRACTION_BROWSER_LAUNCH_TIMEOUT)
            print("  [Extração] Navegador lançado.")
            context_extract = browser_extract.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                java_script_enabled=True, ignore_https_errors=True, accept_downloads=False,
                viewport={'width': 1280, 'height': 900}
            )
            page_extract = context_extract.new_page()
            page_extract.set_default_navigation_timeout(EXTRACTION_PAGE_NAVIGATION_TIMEOUT)
            page_extract.set_default_timeout(EXTRACTION_DEFAULT_OPERATION_TIMEOUT)

            print(f"  [Extração] Navegando para: {url}...")
            nav_error_message = None
            try:
                response = page_extract.goto(url, wait_until="domcontentloaded")
                if response and not response.ok:
                     print(f"  [Extração] Aviso: Página retornou status não OK: {response.status} para {url}")
                     if 400 <= response.status < 600 :
                         nav_error_message = f"FALHA NA EXTRAÇÃO: Página retornou status {response.status}."
            except PlaywrightError as e_goto:
                error_msg = str(e_goto).lower()
                if "net::err_name_not_resolved" in error_msg: nav_error_message = "FALHA NA EXTRAÇÃO: ERRO DE DNS."
                elif "net::err_connection_refused" in error_msg: nav_error_message = "FALHA NA EXTRAÇÃO: CONEXÃO RECUSADA."
                elif "net::err_aborted" in error_msg and is_social_media:
                    print(f"  [Extração] Aviso: Navegação abortada (comum em SMedia). Tentando prosseguir. {url}")
                elif "timeout" in error_msg:
                    nav_error_message = "FALHA NA EXTRAÇÃO: TIMEOUT NA NAVEGAÇÃO."
                else:
                    print(f"  [Extração] Erro Playwright durante goto para {url}: {type(e_goto).__name__} - {e_goto}")
                    try:
                        print(f"    Tentando recarregar a página {url} uma vez...")
                        page_extract.reload(wait_until="domcontentloaded") # type: ignore
                        print(f"    Página recarregada.")
                    except Exception as e_reload:
                        print(f"    Falha ao recarregar a página: {e_reload}")
                        nav_error_message = f"FALHA NA EXTRAÇÃO: ERRO GOTO SEGUIDO DE FALHA NO RELOAD ({type(e_goto).__name__})."
            
            if nav_error_message:
                return nav_error_message, None, nav_error_message

            print(f"  [Extração] Página '{url}' DOM carregado (ou tentativa continuada).")

            try:
                print(f"    Esperando networkidle (max {EXTRACTION_NETWORKIDLE_TIMEOUT/1000}s)...")
                page_extract.wait_for_load_state("networkidle", timeout=EXTRACTION_NETWORKIDLE_TIMEOUT)
                print("    Networkidle concluído.")
            except PlaywrightTimeoutError:
                print("    Timeout esperando networkidle, continuando mesmo assim...")

            pause_duration = SOCIAL_MEDIA_EXTRACTION_PAUSE if is_social_media else 2500
            if is_social_media:
                print(f"    Rede social detectada. Pausa ({pause_duration/1000}s) e scroll...")
                page_extract.wait_for_timeout(pause_duration / 2)
                for i in range(3):
                    if page_extract.is_closed(): break
                    page_extract.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                    time.sleep(0.8 + i * 0.2)
                page_extract.wait_for_timeout(pause_duration / 2)
            else:
                page_extract.wait_for_timeout(pause_duration)

            if page_extract.is_closed(): return "FALHA NA EXTRAÇÃO: Página fechada inesperadamente.", None, "FALHA NA EXTRAÇÃO: Página fechada inesperadamente."

            page_img_bytes_for_ia = get_screenshot_bytes(page_extract, full_page=True)
            if page_img_bytes_for_ia:
                 try:
                    with open(page_screenshot_path_candidate, "wb") as f_img: f_img.write(page_img_bytes_for_ia)
                    final_screenshot_path = page_screenshot_path_candidate
                    print(f"  [Extração] Screenshot salvo em: {os.path.basename(final_screenshot_path)}")
                 except Exception as e_save_ss:
                    print(f"  [Extração] Aviso: Falha ao salvar screenshot em {page_screenshot_path_candidate}: {e_save_ss}")
                    final_screenshot_path = None
            else:
                 print(f"  [Extração] Não foi possível obter screenshot principal para {url}.")


            print(f"  [Extração] Executando script JS para extrair texto de {url}...")
            extraction_js_script = r"""
                () => {
                    const removeElements = (root, selectors) => {
                        try { root.querySelectorAll(selectors.join(',')).forEach(el => el.remove()); }
                        catch (e) { /* console.warn('JS Warn: Error removing selectors:', e.message, selectors); */ }
                    };
                    let contentRoot = document.body ? document.body.cloneNode(true) : (document.documentElement ? document.documentElement.cloneNode(true) : null);
                    if (!contentRoot) return "ERRO INTERNO JS: contentRoot (body/documentElement) não encontrado.";

                    const selectorsToRemove = [
                        'script', 'style', 'noscript', 'svg', 'iframe', 'link', 'meta', 'button', 'input', 'select', 'textarea', 'form',
                        'nav', 'header', 'footer', 'aside', '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
                        '[role="search"]', '[role="complementary"]', '[role="form"]', '[role="application"]', '[role="menu"]',
                        '[aria-hidden="true"]', '[hidden]', '[style*="display:none"]', '[style*="visibility:hidden"]',
                        '.cookie-banner', '.cookie-consent', '#cookie-banner', '#cookie-consent', '[class*="cookie"]', '[id*="cookie"]',
                        '.modal', '.popup', '[role="dialog"]', '[class*="modal"]', '[class*="popup"]', '[id*="modal"]', '[id*="popup"]',
                        '.advertisement', '.ad', '[class*="ad-"]', '[id*="ad-"]', '[class*="sponsor"]',
                        '.sidebar', '.widget', '.related-posts', '.comments', '.share-buttons', '.social-media-links', '.pagination',
                        'figure:not(:has(figcaption))', 'img:not([alt])', 'picture:not(:has(img[alt]))',
                        'video:not([aria-label])', 'audio:not([aria-label])',
                        '[data-nosnippet]', '.visually-hidden', '.sr-only',
                        '[id*="chat"], [class*="chat"], [id*="intercom"], [class*="intercom"], [id*="drift"], [class*="drift"]',
                        '[id*="livezilla"], [class*="livezilla"], [id*="tawk"], [class*="tawk"]',
                        '[class*="optin"], [class*="subscribe"], [class*="newsletter"]'
                    ];
                    removeElements(contentRoot, selectorsToRemove);

                    const mainContentSelectors = [
                        'article[class*="body"]', 'div[class*="article-body"]', 'main[role="main"]', 'div[role="main"]',
                        'main', 'article', '.content', '.entry-content', '.post-content', '.page-content',
                        '#content', '#main-content', '#main',
                        'div[data-testid="UserDescription"]', 'h1',
                        'section#profile-summary', 'section.pv-profile-section--summary',
                        'div.feed-shared-update-v2__description-wrapper', 'div[role="article"]', '.prose',
                        'div.main', 'div.container', 'section.content', 'div.page__content',
                        'div[itemprop="articleBody"]'
                    ];

                    let extractedTexts = []; let mainContentFound = false;
                    for (const selector of mainContentSelectors) {
                        try {
                            const elements = contentRoot.querySelectorAll(selector);
                            if (elements.length > 0) {
                                elements.forEach(el => {
                                    const text = el.innerText || "";
                                    if (text.trim()) extractedTexts.push(text.trim());
                                });
                                mainContentFound = true;
                                if (!document.domain.includes("instagram.com") && !document.domain.includes("linkedin.com")) break;
                            }
                        } catch (e) { /* console.warn('JS Warn: Error querying main selector:', e.message, selector); */ }
                    }

                    if (!mainContentFound || document.domain.includes("instagram.com") || document.domain.includes("linkedin.com")) {
                        try {
                            const bodyText = contentRoot.innerText || "";
                            if (bodyText.trim()) extractedTexts.push(bodyText.trim());
                        } catch (e) { /* console.warn('JS Warn: Error getting innerText of contentRoot:', e.message); */ }
                    }

                    if (extractedTexts.length === 0) return "";
                    let combinedText = extractedTexts.join("\n\n");
                    let cleanedText = combinedText
                        .replace(/[ \t\u00A0\u200B-\u200D\uFEFF]+/g, ' ')
                        .replace(/(\r\n|\r|\n){3,}/g, '\n\n')
                        .replace(/^[\s\n]+|[\s\n]+$/g, '');
                    cleanedText = cleanedText.split('\n').map(line => line.trim()).filter(line => {
                        if (line.length === 0) return false;
                        if (document.domain.includes("instagram.com") || document.domain.includes("linkedin.com")) return line.length > 1;
                        const alphaNumericCount = (line.match(/[a-zA-Z0-9À-ÖØ-öø-ÿ]/g) || []).length;
                        if (line.length < 30 && alphaNumericCount < line.length * 0.35) return false;
                        if (line.length < 8 && alphaNumericCount < 3) return false;
                        if (/^https?:\/\/\S+$/.test(line) && line.length < 30) return false;
                        if (/^\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}$/.test(line)) return false;
                        return true;
                    }).join('\n');
                    return cleanedText.trim();
                }
            """
            js_error_message = None
            try:
                extracted_text_dom = page_extract.evaluate(extraction_js_script)
                print(f"  [Extração DOM] Texto extraído (bruto: {len(extracted_text_dom or '')} chars).")
                if extracted_text_dom == "ERRO INTERNO JS: contentRoot (body/documentElement) não encontrado.":
                    js_error_message = extracted_text_dom
            except PlaywrightError as e_eval:
                error_str_eval = str(e_eval).lower()
                if "execution context was destroyed" in error_str_eval: js_error_message = "FALHA NA EXTRAÇÃO DOM: CONTEXTO DESTRUÍDO."
                elif "timeout" in error_str_eval and "page.evaluate" in error_str_eval: js_error_message = "FALHA NA EXTRAÇÃO DOM: TIMEOUT SCRIPT JS."
                else: js_error_message = f"FALHA NA EXTRAÇÃO DOM: ERRO PLAYWRIGHT SCRIPT JS - {type(e_eval).__name__}."
                print(f"  [Extração DOM] Erro Playwright ao executar script JS: {js_error_message} - {e_eval}")
            except Exception as e_eval_general:
                js_error_message = f"FALHA NA EXTRAÇÃO DOM: ERRO GERAL SCRIPT JS - {type(e_eval_general).__name__}."
                print(f"  [Extração DOM] Erro GERAL ao executar script JS: {js_error_message} - {e_eval_general}")
            
            if js_error_message: extracted_text_dom = js_error_message

            extraction_via_dom_successful = extracted_text_dom and "FALHA NA EXTRAÇÃO DOM" not in extracted_text_dom and "ERRO INTERNO JS" not in extracted_text_dom and len(extracted_text_dom) >= 150

            if page_img_bytes_for_ia and not extraction_via_dom_successful:
                print(f"  [Extração Multimodal] Extração DOM fraca/falhou ('{extracted_text_dom[:50] if extracted_text_dom else ''}...'). Tentando análise de imagem para {url}...")
                multimodal_prompt = (
                    "Analise a imagem desta página web. Descreva o conteúdo principal, o tipo de página (ex: blog, loja, perfil social), "
                    "e qualquer texto proeminente ou informação chave visível. Se for um erro, página de login, ou conteúdo irrelevante, mencione isso."
                )
                ia_vision_text = ask_gemini_about_image(page_img_bytes_for_ia, multimodal_prompt)
                if ia_vision_text and "FALHA IA IMAGEM" not in ia_vision_text:
                    print(f"    [Extração Multimodal] Texto obtido da IA Visual: {ia_vision_text[:150]}...")
                    if extracted_text_dom and "FALHA NA EXTRAÇÃO DOM" not in extracted_text_dom and "ERRO INTERNO JS" not in extracted_text_dom and len(extracted_text_dom) > 30:
                        extracted_text_dom = f"TEXTO DO DOM (PARCIAL):\n{extracted_text_dom}\n\nANÁLISE COMPLEMENTAR DA IMAGEM PELA IA:\n{ia_vision_text}"
                    else:
                        extracted_text_dom = f"ANÁLISE DA IMAGEM PELA IA (EXTRAÇÃO DOM FRACA/FALHOU):\n{ia_vision_text}"
                elif ia_vision_text:
                     print(f"    [Extração Multimodal] Falha na análise visual da IA: {ia_vision_text}")
                     if not extracted_text_dom or "FALHA NA EXTRAÇÃO DOM" in extracted_text_dom or "ERRO INTERNO JS" in extracted_text_dom:
                         extracted_text_dom = f"FALHA NA EXTRAÇÃO: DOM FALHOU E {ia_vision_text}"
                else:
                    print(f"    [Extração Multimodal] IA visual não retornou texto descritivo.")
                    if not extracted_text_dom or "FALHA NA EXTRAÇÃO DOM" in extracted_text_dom or "ERRO INTERNO JS" in extracted_text_dom:
                         extracted_text_dom = "FALHA NA EXTRAÇÃO: DOM FALHOU, IA VISUAL SEM RETORNO."
            elif not page_img_bytes_for_ia and not extraction_via_dom_successful:
                print(f"  [Extração] Extração DOM fraca/falhou e não foi possível obter screenshot para análise visual.")


        except Exception as e_extract_setup:
            print(f"  [Extração] Erro CRÍTICO no setup do Playwright para extração de {url}: {type(e_extract_setup).__name__} - {e_extract_setup}")
            traceback.print_exc()
            return f"FALHA NA EXTRAÇÃO: ERRO CRÍTICO NO PLAYWRIGHT SETUP - {type(e_extract_setup).__name__}.", None, f"FALHA NA EXTRAÇÃO: ERRO CRÍTICO NO PLAYWRIGHT SETUP - {type(e_extract_setup).__name__}."
        finally:
            print(f"  [Extração] Finalizando sessão de extração para {url}...")
            if page_extract and not page_extract.is_closed():
                try: page_extract.close()
                except Exception: pass
            if context_extract:
                try: context_extract.close()
                except Exception: pass
            if browser_extract and browser_extract.is_connected():
                try: browser_extract.close()
                except Exception: pass
            print(f"  [Extração] Sessão de extração para {url} finalizada.")

    final_text_to_return = extracted_text_dom
    extraction_status_message = "SUCESSO NA EXTRAÇÃO"

    if not final_text_to_return or not final_text_to_return.strip():
        extraction_status_message = "FALHA NA EXTRAÇÃO: NENHUM TEXTO OBTIDO."
        final_text_to_return = extraction_status_message
    elif "FALHA NA EXTRAÇÃO" in final_text_to_return or "FALHA IA IMAGEM" in final_text_to_return or "ERRO INTERNO JS" in final_text_to_return:
        extraction_status_message = final_text_to_return
    else:
        lines = [line.strip() for line in final_text_to_return.splitlines() if line.strip()]
        final_text_to_return = "\n".join(lines)
        if len(final_text_to_return) > GEMINI_MAX_TEXT_INPUT_CHARS:
             print(f"  [Extração] Aviso: Texto final de {url} truncado para {GEMINI_MAX_TEXT_INPUT_CHARS} caracteres.")
             final_text_to_return = final_text_to_return[:GEMINI_MAX_TEXT_INPUT_CHARS]
        if not final_text_to_return.strip():
            extraction_status_message = "FALHA NA EXTRAÇÃO: TEXTO EXTRAÍDO FICOU VAZIO APÓS LIMPEZA."
            final_text_to_return = extraction_status_message
        elif "ANÁLISE DA IMAGEM PELA IA" in final_text_to_return:
            extraction_status_message = "SUCESSO NA EXTRAÇÃO (VIA ANÁLISE DE IMAGEM)"
    return final_text_to_return, final_screenshot_path, extraction_status_message


# --- Execução Principal do Script ---
if __name__ == "__main__":
    main_start_time = time.time()
    results_filepath = ""
    user_search_query = ""

    try:
        user_search_query = input("Digite o que você quer pesquisar no Google (ex: 'empresas de software em São Paulo'): ")
        if not user_search_query.strip():
            print("Nenhum termo de pesquisa fornecido. Encerrando.")
            sys.exit(1)

        NUM_SITES_TO_PROCESS = 10
        max_possible_sites = MAX_PAGES_TO_SCRAPE_GOOGLE * MAX_RESULTS_PER_GOOGLE_PAGE_APPROX
        while True:
            try:
                num_sites_str = input(f"Quantos sites você gostaria de extrair (padrão: 10, max: {max_possible_sites})? ")
                if not num_sites_str.strip():
                    NUM_SITES_TO_PROCESS = 10
                    print(f"Usando padrão: {NUM_SITES_TO_PROCESS} sites.")
                    break
                cleaned_num_sites_str = re.sub(r'\D', '', num_sites_str)
                if not cleaned_num_sites_str:
                    print(f"Entrada inválida (não numérica). Usando padrão: {NUM_SITES_TO_PROCESS} sites.")
                    NUM_SITES_TO_PROCESS = 10
                    break
                num_input = int(cleaned_num_sites_str)

                if 0 < num_input <= max_possible_sites:
                    NUM_SITES_TO_PROCESS = num_input
                    break
                elif num_input > max_possible_sites:
                    print(f"Número muito alto. O máximo permitido é {max_possible_sites}. Tente novamente.")
                else:
                    print("Por favor, insira um número positivo. Tente novamente.")
            except ValueError:
                print("Entrada inválida. Por favor, insira um número. Tente novamente.")

        print(f"Objetivo: Extrair dados de até {NUM_SITES_TO_PROCESS} sites.")

        google_results_data = search_google_and_get_top_n_links(user_search_query, num_links_target=NUM_SITES_TO_PROCESS)

        if not google_results_data:
            print(f"\nNenhum resultado do Google utilizável encontrado para a busca: '{user_search_query}'.")
        else:
            print(f"\n--- Iniciando Extração de Texto para {len(google_results_data)} Resultados do Google Coletados ---")

        all_extracted_data = []
        if google_results_data: # Só processa se houver resultados do Google
            for i, result_item in enumerate(google_results_data):
                current_url = result_item["url"]
                google_title = result_item["title"]
                google_snippet = result_item["snippet"]

                print(f"\n--- Processando URL {i+1}/{len(google_results_data)}: {current_url} ---")
                print(f"    Título Google: {google_title}")
                print(f"    Snippet Google: {google_snippet[:100]}...")

                if i > 0: time.sleep(2.0)

                extracted_text, screenshot_file, extraction_status = extract_text_from_url(current_url)

                relative_screenshot_path = None
                if screenshot_file:
                    try:
                        if OUTPUT_FOLDER in screenshot_file and os.path.abspath(OUTPUT_FOLDER) in os.path.abspath(screenshot_file):
                             relative_screenshot_path = os.path.relpath(screenshot_file, start=OUTPUT_FOLDER)
                        else:
                             relative_screenshot_path = os.path.relpath(screenshot_file, start=os.getcwd()) \
                                if os.path.abspath(os.getcwd()) in os.path.abspath(screenshot_file) \
                                else screenshot_file
                    except ValueError:
                        relative_screenshot_path = screenshot_file

                current_url_payload = {
                    "url": current_url,
                    "google_search_data": {"title": google_title, "snippet": google_snippet},
                    "extracted_text_content": extracted_text,
                    "extraction_status_message": extraction_status,
                    "screenshot_filepath": relative_screenshot_path
                }

                all_extracted_data.append(current_url_payload)
                print(f"    Status da Extração: {extraction_status}")
                if relative_screenshot_path:
                     print(f"    Caminho do Screenshot (relativo/absoluto): {relative_screenshot_path}")
                print("----------------------------------------------------")

        output_json = {
            "original_query": user_search_query,
            "collection_timestamp": datetime.datetime.now().isoformat(),
            "total_sites_targeted_for_processing": len(google_results_data) if google_results_data else 0,
            "total_sites_processed_in_extraction_phase": len(all_extracted_data),
            "sites_data": all_extracted_data
        }

        timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_query_filename = make_safe_filename(user_search_query, 30)
        results_filename = f"harvested_data_{safe_query_filename}_{timestamp_str}.json"
        results_filepath = os.path.join(OUTPUT_FOLDER, results_filename)

        try:
            with open(results_filepath, "w", encoding="utf-8") as f:
                json.dump(output_json, f, ensure_ascii=False, indent=2)

            successful_extractions = sum(1 for item in all_extracted_data if "SUCESSO" in item["extraction_status_message"])
            print(f"\nDados extraídos ({successful_extractions} com texto útil, de {len(all_extracted_data)} URLs processadas) salvos em: {results_filepath}")
        except Exception as e_save:
            print(f"Erro ao salvar dados extraídos em JSON: {e_save} (Caminho: {results_filepath})")
            traceback.print_exc()

    except KeyboardInterrupt:
        print("\nOperação interrompida pelo usuário.")
    except Exception as e_main_script:
        print(f"\nErro CRÍTICO INESPERADO no script principal: {type(e_main_script).__name__} - {e_main_script}")
        traceback.print_exc()
    finally:
        main_end_time = time.time()
        print(f"\nTempo total de execução do script Harvester: {main_end_time - main_start_time:.2f} segundos.")