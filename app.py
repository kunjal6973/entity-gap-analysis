import streamlit as st
import textrazor
import pandas as pd
from collections import defaultdict

def extract_entities(url, client):
    """
    Extract entities from a given URL using TextRazor.
    Returns a dictionary of entity information.
    """
    try:
        response = client.analyze_url(url)
        entities = {}

        for entity in response.entities():
            # Skip entities with low confidence or relevance
            if entity.confidence_score < 0.5 or entity.relevance_score < 0.2:
                continue

            # Determine entity type (Organization, Person, Location, or Other)
            entity_type = "Other"
            if entity.freebase_types:
                for t in entity.freebase_types:
                    if any(category in t for category in ['organization', 'company']):
                        entity_type = "Organization"
                    elif 'person' in t:
                        entity_type = "Person"
                    elif any(category in t for category in ['location', 'place']):
                        entity_type = "Location"

            if entity.id not in entities:
                entities[entity.id] = {
                    'count': 1,
                    'type': entity_type,
                    'relevance': entity.relevance_score,
                    'confidence': entity.confidence_score
                }
            else:
                entities[entity.id]['count'] += 1

        return entities
    except Exception as e:
        st.warning(f"Error processing {url}: {str(e)}")
        return {}


def main():
    st.title("Competitive Entity Analysis")

    st.subheader("Step 1: Enter TextRazor API Key")
    api_key = st.text_input("TextRazor API Key", type="password")

    st.subheader("Step 2: Provide Main URL")
    main_url = st.text_input("Main URL", "")

    st.subheader("Step 3: Provide Competitor URLs (one per line)")
    competitors_input = st.text_area("Competitor URLs", "")
    competitor_urls = [url.strip() for url in competitors_input.splitlines() if url.strip()]

    if st.button("Analyze"):
        if not api_key:
            st.error("Please provide your TextRazor API key.")
            return
        if not main_url:
            st.error("Please provide the main URL.")
            return
        if not competitor_urls:
            st.error("Please provide at least one competitor URL.")
            return

        # Set up TextRazor client
        textrazor.api_key = api_key
        client = textrazor.TextRazor(extractors=["entities", "topics"])

        # Analyze main URL
        st.write("Analyzing main URL...")
        main_entities = extract_entities(main_url, client)

        # Analyze competitor URLs
        st.write("Analyzing competitor URLs...")
        competitor_entities = {}
        for url in competitor_urls:
            competitor_entities[url] = extract_entities(url, client)

        # Build a dictionary of entities that appear in competitor URLs
        # but NOT in the main URL:
        missed_entities = defaultdict(lambda: {'count': 0, 'type': '', 'sources': []})

        for url, entities in competitor_entities.items():
            for entity_id, info in entities.items():
                # If entity is missing from main URL
                if entity_id not in main_entities:
                    missed_entities[entity_id]['count'] += info['count']
                    missed_entities[entity_id]['type'] = info['type']
                    missed_entities[entity_id]['sources'].append(url)

        # Create DataFrame but only include entities that appear in AT LEAST 2 competitor URLs
        df_data = []
        for entity_id, info in missed_entities.items():
            found_in_count = len(info['sources'])

            if found_in_count >= 2:  # "More than 1 competitor"
                df_data.append({
                    'Entity': entity_id,
                    'Type': info['type'],
                    'Total Mentions': info['count'],
                    'Found In': found_in_count,
                    'Sources': ', '.join(info['sources'])
                })

        df = pd.DataFrame(df_data)

        # Safely sort the DataFrame if it isn't empty
        if not df.empty:
            df = df.sort_values('Total Mentions', ascending=False)
            st.subheader("Entities Mentioned by More Than 1 Competitor (but Missing in Main URL):")
            st.dataframe(df)

            # Optional: allow downloading the CSV
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="competitive_entity_analysis.csv",
                mime="text/csv",
            )
        else:
            st.info("No entities found that match the criteria (i.e., used by more than one competitor but missing in your URL).")

if __name__ == "__main__":
    main()
