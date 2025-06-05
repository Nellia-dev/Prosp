import { MigrationInterface, QueryRunner } from 'typeorm';

export class InitialMigration1699000000000 implements MigrationInterface {
  name = 'InitialMigration1699000000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Create enums first
    await queryRunner.query(`
      CREATE TYPE "agent_name_enum" AS ENUM (
        'lead_intake_agent',
        'lead_analysis_agent',
        'enhanced_lead_processor',
        'tavily_enrichment_agent',
        'contact_extraction_agent',
        'pain_point_deepening_agent',
        'lead_qualification_agent',
        'competitor_identification_agent',
        'strategic_question_generation_agent',
        'buying_trigger_identification_agent',
        'tot_strategy_generation_agent',
        'tot_strategy_evaluation_agent',
        'tot_action_plan_synthesis_agent',
        'detailed_approach_plan_agent',
        'objection_handling_agent',
        'value_proposition_customization_agent',
        'b2b_personalized_message_agent',
        'internal_briefing_summary_agent',
        'approach_strategy_agent',
        'b2b_persona_creation_agent',
        'message_crafting_agent',
        'persona_creation_agent',
        'lead_analysis_generation_agent'
      )
    `);

    await queryRunner.query(`
      CREATE TYPE "agent_status_enum" AS ENUM (
        'active',
        'inactive',
        'processing',
        'error',
        'completed'
      )
    `);

    await queryRunner.query(`
      CREATE TYPE "agent_category_enum" AS ENUM (
        'initial_processing',
        'orchestrator',
        'specialized',
        'alternative'
      )
    `);

    await queryRunner.query(`
      CREATE TYPE "processing_stage_enum" AS ENUM (
        'lead_qualification',
        'analyzing_refining',
        'possibly_qualified',
        'prospecting',
        'revisando',
        'primeiras_mensagens',
        'negociando',
        'desqualificado',
        'reuniao_agendada',
        'intake',
        'analysis',
        'persona',
        'strategy',
        'message',
        'completed'
      )
    `);

    await queryRunner.query(`
      CREATE TYPE "qualification_tier_enum" AS ENUM (
        'High Potential',
        'Medium Potential',
        'Low Potential'
      )
    `);

    await queryRunner.query(`
      CREATE TYPE "user_role_enum" AS ENUM (
        'admin',
        'user'
      )
    `);

    await queryRunner.query(`
      CREATE TYPE "chat_message_type_enum" AS ENUM (
        'user',
        'agent'
      )
    `);

    // Create users table
    await queryRunner.query(`
      CREATE TABLE "users" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "email" character varying(255) NOT NULL,
        "password" character varying(255) NOT NULL,
        "first_name" character varying(100) NOT NULL,
        "last_name" character varying(100) NOT NULL,
        "role" "user_role_enum" NOT NULL DEFAULT 'user',
        "is_active" boolean NOT NULL DEFAULT true,
        "last_login" TIMESTAMP,
        "created_at" TIMESTAMP NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
        CONSTRAINT "PK_users" PRIMARY KEY ("id")
      )
    `);

    await queryRunner.query(`
      CREATE UNIQUE INDEX "IDX_users_email" ON "users" ("email")
    `);

    // Create business_context table
    await queryRunner.query(`
      CREATE TABLE "business_context" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "business_description" text NOT NULL,
        "target_market" text NOT NULL,
        "value_proposition" text NOT NULL,
        "ideal_customer" text NOT NULL,
        "pain_points" text array NOT NULL DEFAULT '{}',
        "competitive_advantage" text NOT NULL,
        "industry_focus" text array NOT NULL DEFAULT '{}',
        "geographic_focus" text array NOT NULL DEFAULT '{Brasil}',
        "is_active" boolean NOT NULL DEFAULT true,
        "created_at" TIMESTAMP NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
        CONSTRAINT "PK_business_context" PRIMARY KEY ("id")
      )
    `);

    // Create agents table
    await queryRunner.query(`
      CREATE TABLE "agents" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "name" "agent_name_enum" NOT NULL,
        "status" "agent_status_enum" NOT NULL DEFAULT 'inactive',
        "metrics" jsonb NOT NULL,
        "currentTask" character varying,
        "description" text,
        "category" "agent_category_enum",
        "created_at" TIMESTAMP NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
        "last_updated" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "throughput" integer NOT NULL DEFAULT 0,
        "llmTokenUsage" integer NOT NULL DEFAULT 0,
        "successRate" decimal(5,2) NOT NULL DEFAULT 0,
        "queueDepth" integer NOT NULL DEFAULT 0,
        "processingTime" decimal(8,2) NOT NULL DEFAULT 0,
        CONSTRAINT "PK_agents" PRIMARY KEY ("id")
      )
    `);

    // Create leads table
    await queryRunner.query(`
      CREATE TABLE "leads" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "company_name" character varying NOT NULL,
        "website" character varying NOT NULL,
        "relevance_score" decimal(3,2) NOT NULL,
        "roi_potential_score" decimal(3,2) NOT NULL,
        "brazilian_market_fit" decimal(3,2) NOT NULL,
        "qualification_tier" "qualification_tier_enum" NOT NULL,
        "company_sector" character varying NOT NULL,
        "persona" jsonb,
        "pain_point_analysis" text array,
        "purchase_triggers" text array,
        "processing_stage" "processing_stage_enum" NOT NULL DEFAULT 'intake',
        "created_at" TIMESTAMP NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
        "description" character varying,
        "contact_email" character varying,
        "contact_phone" character varying,
        "contact_role" character varying,
        "market_region" character varying,
        "company_size" character varying,
        "annual_revenue" decimal(15,2),
        "persona_analysis" text,
        "decision_maker_probability" decimal(3,2),
        CONSTRAINT "PK_leads" PRIMARY KEY ("id")
      )
    `);

    // Create chat_messages table
    await queryRunner.query(`
      CREATE TABLE "chat_messages" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "agent_id" uuid NOT NULL,
        "content" text NOT NULL,
        "type" "chat_message_type_enum" NOT NULL,
        "attachments" text array,
        "timestamp" TIMESTAMP NOT NULL DEFAULT now(),
        "created_at" TIMESTAMP NOT NULL DEFAULT now(),
        CONSTRAINT "PK_chat_messages" PRIMARY KEY ("id")
      )
    `);

    // Add foreign key constraint
    await queryRunner.query(`
      ALTER TABLE "chat_messages" 
      ADD CONSTRAINT "FK_chat_messages_agent" 
      FOREIGN KEY ("agent_id") REFERENCES "agents"("id") ON DELETE CASCADE
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Drop tables in reverse order
    await queryRunner.query(`DROP TABLE "chat_messages"`);
    await queryRunner.query(`DROP TABLE "leads"`);
    await queryRunner.query(`DROP TABLE "agents"`);
    await queryRunner.query(`DROP TABLE "business_context"`);
    await queryRunner.query(`DROP TABLE "users"`);

    // Drop enums
    await queryRunner.query(`DROP TYPE "chat_message_type_enum"`);
    await queryRunner.query(`DROP TYPE "user_role_enum"`);
    await queryRunner.query(`DROP TYPE "qualification_tier_enum"`);
    await queryRunner.query(`DROP TYPE "processing_stage_enum"`);
    await queryRunner.query(`DROP TYPE "agent_category_enum"`);
    await queryRunner.query(`DROP TYPE "agent_status_enum"`);
    await queryRunner.query(`DROP TYPE "agent_name_enum"`);
  }
}