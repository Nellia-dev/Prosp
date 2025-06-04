import { MigrationInterface, QueryRunner } from "typeorm";

export class InitialSchema1735993736000 implements MigrationInterface {
    name = 'InitialSchema1735993736000'

    public async up(queryRunner: QueryRunner): Promise<void> {
        // Create users table
        await queryRunner.query(`
            CREATE TABLE "users" (
                "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
                "email" character varying(255) NOT NULL,
                "password" character varying(255) NOT NULL,
                "first_name" character varying(100) NOT NULL,
                "last_name" character varying(100) NOT NULL,
                "role" "public"."users_role_enum" NOT NULL DEFAULT 'user',
                "is_active" boolean NOT NULL DEFAULT true,
                "last_login" TIMESTAMP,
                "created_at" TIMESTAMP NOT NULL DEFAULT now(),
                "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
                CONSTRAINT "UQ_97672ac88f789774dd47f7c8be3" UNIQUE ("email"),
                CONSTRAINT "PK_a3ffb1c0c8416b9fc6f907b7433" PRIMARY KEY ("id")
            )
        `);

        // Create user role enum
        await queryRunner.query(`
            CREATE TYPE "public"."users_role_enum" AS ENUM('admin', 'user')
        `);

        // Create agents table
        await queryRunner.query(`
            CREATE TABLE "agents" (
                "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
                "name" "public"."agents_name_enum" NOT NULL,
                "status" "public"."agents_status_enum" NOT NULL DEFAULT 'inactive',
                "metrics" jsonb NOT NULL,
                "current_task" character varying,
                "created_at" TIMESTAMP NOT NULL DEFAULT now(),
                "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
                "last_updated" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT "PK_68dd9b6fe41c6f2b5c6c58a6b34" PRIMARY KEY ("id")
            )
        `);

        // Create agent name enum
        await queryRunner.query(`
            CREATE TYPE "public"."agents_name_enum" AS ENUM('lead_intake', 'analysis', 'persona_creation', 'approach_strategy', 'message_crafting')
        `);

        // Create agent status enum
        await queryRunner.query(`
            CREATE TYPE "public"."agents_status_enum" AS ENUM('active', 'inactive', 'processing', 'error', 'completed')
        `);

        // Create leads table
        await queryRunner.query(`
            CREATE TABLE "leads" (
                "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
                "company_name" character varying NOT NULL,
                "website" character varying NOT NULL,
                "relevance_score" numeric(3,2) NOT NULL,
                "roi_potential_score" numeric(3,2) NOT NULL,
                "brazilian_market_fit" numeric(3,2) NOT NULL,
                "qualification_tier" "public"."leads_qualification_tier_enum" NOT NULL,
                "company_sector" character varying NOT NULL,
                "persona" jsonb,
                "pain_point_analysis" text array,
                "purchase_triggers" text array,
                "processing_stage" "public"."leads_processing_stage_enum" NOT NULL DEFAULT 'intake',
                "created_at" TIMESTAMP NOT NULL DEFAULT now(),
                "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
                CONSTRAINT "PK_343a9d12ba12d4d1beb5c1f3c18" PRIMARY KEY ("id")
            )
        `);

        // Create leads qualification tier enum
        await queryRunner.query(`
            CREATE TYPE "public"."leads_qualification_tier_enum" AS ENUM('High Potential', 'Medium Potential', 'Low Potential')
        `);

        // Create leads processing stage enum
        await queryRunner.query(`
            CREATE TYPE "public"."leads_processing_stage_enum" AS ENUM('intake', 'analysis', 'persona', 'strategy', 'message', 'completed')
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
                CONSTRAINT "PK_8f5f8b3b8e8e8d4e8e8d4e8e8d4" PRIMARY KEY ("id")
            )
        `);

        // Create chat_messages table
        await queryRunner.query(`
            CREATE TABLE "chat_messages" (
                "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
                "agent_id" uuid NOT NULL,
                "content" text NOT NULL,
                "type" "public"."chat_messages_type_enum" NOT NULL,
                "attachments" text array,
                "timestamp" TIMESTAMP NOT NULL DEFAULT now(),
                "created_at" TIMESTAMP NOT NULL DEFAULT now(),
                CONSTRAINT "PK_5ec46e1b24ee6b6e3b4e4b4e4b4" PRIMARY KEY ("id")
            )
        `);

        // Create chat message type enum
        await queryRunner.query(`
            CREATE TYPE "public"."chat_messages_type_enum" AS ENUM('user', 'agent')
        `);

        // Create foreign key constraint for chat_messages -> agents
        await queryRunner.query(`
            ALTER TABLE "chat_messages" ADD CONSTRAINT "FK_chat_messages_agent_id" FOREIGN KEY ("agent_id") REFERENCES "agents"("id") ON DELETE NO ACTION ON UPDATE NO ACTION
        `);

        // Create indexes
        await queryRunner.query(`
            CREATE UNIQUE INDEX "IDX_97672ac88f789774dd47f7c8be" ON "users" ("email")
        `);
    }

    public async down(queryRunner: QueryRunner): Promise<void> {
        // Drop foreign key constraints
        await queryRunner.query(`ALTER TABLE "chat_messages" DROP CONSTRAINT "FK_chat_messages_agent_id"`);

        // Drop indexes
        await queryRunner.query(`DROP INDEX "public"."IDX_97672ac88f789774dd47f7c8be"`);

        // Drop tables
        await queryRunner.query(`DROP TABLE "chat_messages"`);
        await queryRunner.query(`DROP TABLE "business_context"`);
        await queryRunner.query(`DROP TABLE "leads"`);
        await queryRunner.query(`DROP TABLE "agents"`);
        await queryRunner.query(`DROP TABLE "users"`);

        // Drop enums
        await queryRunner.query(`DROP TYPE "public"."chat_messages_type_enum"`);
        await queryRunner.query(`DROP TYPE "public"."leads_processing_stage_enum"`);
        await queryRunner.query(`DROP TYPE "public"."leads_qualification_tier_enum"`);
        await queryRunner.query(`DROP TYPE "public"."agents_status_enum"`);
        await queryRunner.query(`DROP TYPE "public"."agents_name_enum"`);
        await queryRunner.query(`DROP TYPE "public"."users_role_enum"`);
    }
}