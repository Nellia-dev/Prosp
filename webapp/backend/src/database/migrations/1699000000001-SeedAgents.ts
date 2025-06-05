import { MigrationInterface, QueryRunner } from 'typeorm';

export class SeedAgents1699000000001 implements MigrationInterface {
  name = 'SeedAgents1699000000001';

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Default metrics for all agents
    const defaultMetrics = {
      processing_time_seconds: 0,
      llm_usage: {
        total_tokens: 0,
        prompt_tokens: 0,
        completion_tokens: 0
      },
      success_rate: 0,
      queue_depth: 0,
      throughput_per_hour: 0
    };

    // Insert initial processing agents
    await queryRunner.query(`
      INSERT INTO "agents" ("name", "status", "metrics", "description", "category") VALUES 
      ('lead_intake_agent', 'inactive', $1, 'Lead Intake Agent - Initial processing agent', 'initial_processing'),
      ('lead_analysis_agent', 'inactive', $1, 'Lead Analysis Agent - Initial processing agent', 'initial_processing')
    `, [JSON.stringify(defaultMetrics)]);

    // Insert orchestrator agent
    await queryRunner.query(`
      INSERT INTO "agents" ("name", "status", "metrics", "description", "category") VALUES 
      ('enhanced_lead_processor', 'inactive', $1, 'Enhanced Lead Processor - Main orchestrator agent', 'orchestrator')
    `, [JSON.stringify(defaultMetrics)]);

    // Insert specialized agents
    await queryRunner.query(`
      INSERT INTO "agents" ("name", "status", "metrics", "description", "category") VALUES 
      ('tavily_enrichment_agent', 'inactive', $1, 'Web Research Agent - Specialized agent', 'specialized'),
      ('contact_extraction_agent', 'inactive', $1, 'Contact Extraction Agent - Specialized agent', 'specialized'),
      ('pain_point_deepening_agent', 'inactive', $1, 'Pain Point Analysis Agent - Specialized agent', 'specialized'),
      ('lead_qualification_agent', 'inactive', $1, 'Lead Qualification Agent - Specialized agent', 'specialized'),
      ('competitor_identification_agent', 'inactive', $1, 'Competitor Analysis Agent - Specialized agent', 'specialized'),
      ('strategic_question_generation_agent', 'inactive', $1, 'Strategic Questions Agent - Specialized agent', 'specialized'),
      ('buying_trigger_identification_agent', 'inactive', $1, 'Buying Triggers Agent - Specialized agent', 'specialized'),
      ('tot_strategy_generation_agent', 'inactive', $1, 'Strategy Generation Agent - Specialized agent', 'specialized'),
      ('tot_strategy_evaluation_agent', 'inactive', $1, 'Strategy Evaluation Agent - Specialized agent', 'specialized'),
      ('tot_action_plan_synthesis_agent', 'inactive', $1, 'Action Plan Synthesis Agent - Specialized agent', 'specialized'),
      ('detailed_approach_plan_agent', 'inactive', $1, 'Approach Planning Agent - Specialized agent', 'specialized'),
      ('objection_handling_agent', 'inactive', $1, 'Objection Handling Agent - Specialized agent', 'specialized'),
      ('value_proposition_customization_agent', 'inactive', $1, 'Value Proposition Agent - Specialized agent', 'specialized'),
      ('b2b_personalized_message_agent', 'inactive', $1, 'Message Personalization Agent - Specialized agent', 'specialized'),
      ('internal_briefing_summary_agent', 'inactive', $1, 'Internal Briefing Agent - Specialized agent', 'specialized')
    `, [JSON.stringify(defaultMetrics)]);

    // Insert alternative agents
    await queryRunner.query(`
      INSERT INTO "agents" ("name", "status", "metrics", "description", "category") VALUES 
      ('approach_strategy_agent', 'inactive', $1, 'Approach Strategy Agent - Alternative agent', 'alternative'),
      ('b2b_persona_creation_agent', 'inactive', $1, 'B2B Persona Agent - Alternative agent', 'alternative'),
      ('message_crafting_agent', 'inactive', $1, 'Message Crafting Agent - Alternative agent', 'alternative'),
      ('persona_creation_agent', 'inactive', $1, 'Persona Creation Agent - Alternative agent', 'alternative'),
      ('lead_analysis_generation_agent', 'inactive', $1, 'Analysis Generation Agent - Alternative agent', 'alternative')
    `, [JSON.stringify(defaultMetrics)]);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Remove all seeded agents
    await queryRunner.query(`DELETE FROM "agents"`);
  }
}